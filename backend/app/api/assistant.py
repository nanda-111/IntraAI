"""智能客服 API：会话管理、检索增强问答（SSE 流式）与反馈。"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.domains.printer import capabilities, registry
from app.domains.printer.fault_taxonomy import classify_symptom, lookup_error_code
from app.domains.printer.safety_policy import is_high_risk_request, refusal_answer
from app.models.audit import UserFeedback
from app.models.chat_session import PrinterChatMessage, PrinterChatSession
from app.models.printer_brand import PrinterBrand, ProductModel, UserDevice
from app.models.repair_knowledge import RepairKnowledge
from app.models.user import User
from app.schemas.assistant import AssistantMessageCreate, AssistantSessionCreate
from app.schemas.evaluation import FeedbackCreate
from app.services import printer_rag_service

router = APIRouter(prefix="/api/assistant", tags=["智能客服"])

REVIEWED = ("approved", "published")


def session_payload(session: PrinterChatSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "model_id": session.model_id,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def message_payload(message: PrinterChatMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "sources": message.sources or [],
        "intent": message.intent,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _get_session(db: Session, session_id: int, user: User) -> PrinterChatSession:
    session = db.query(PrinterChatSession).filter(PrinterChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    return session


def _default_model(db: Session, user: User) -> str | None:
    device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == user.id, UserDevice.is_current.is_(True))
        .first()
    )
    return device.model_id if device else None


def _model(db: Session, model_id: str | None) -> ProductModel | None:
    if not model_id:
        return None
    return db.query(ProductModel).filter(ProductModel.model_id == model_id).first()


def _history(db: Session, session_id: int, limit: int = 8) -> list[dict]:
    messages = (
        db.query(PrinterChatMessage)
        .filter(PrinterChatMessage.session_id == session_id)
        .order_by(PrinterChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [{"role": message.role, "content": message.content} for message in reversed(messages)]


def _save_message(
    db: Session,
    session: PrinterChatSession,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    intent: str | None = None,
) -> PrinterChatMessage:
    message = PrinterChatMessage(
        session_id=session.id,
        role=role,
        content=content,
        sources=sources or [],
        intent=intent,
    )
    db.add(message)
    session.updated_at = datetime.now()
    db.add(session)
    return message


GENERIC_TROUBLE_WORDS = (
    "不能打印",
    "无法打印",
    "不打印",
    "打印机坏了",
    "有问题",
    "出故障",
    "不工作",
)


def _detect_category(
    db: Session, content: str, model: ProductModel | None, explicit: str | None = None
) -> str | None:
    if explicit:
        return explicit
    code = registry.extract_error_code(content)
    if code and model:
        brand = db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
        mapped = lookup_error_code(brand.brand_code if brand else "", code)
        if mapped:
            return mapped["category"]
    return classify_symptom(content)


def _prepare(
    db: Session,
    session: PrinterChatSession,
    content: str,
    fault_category: str | None = None,
) -> tuple[ProductModel | None, dict | None, str | None]:
    """解析型号上下文、故障类别与检索结果。返回 (model, outcome, direct_answer)。"""
    if is_high_risk_request(content):
        return _model(db, session.model_id), None, refusal_answer()

    model = _model(db, session.model_id)
    if not model:
        resolved = registry.resolve_model(db, text=content)
        candidate = resolved.get("model")
        if candidate and not resolved["requires_confirmation"]:
            session.model_id = candidate.model_id
            model = candidate
        elif content.strip():
            direct = (
                "请先确认打印机的品牌和具体型号（例如 HP DeskJet 2720、Canon TS5380），"
                "这样我才能检索适用于该型号的官方资料。"
            )
            return None, None, direct

    if model and not registry.is_diagnosis_supported(model):
        direct = (
            f"型号 {model.name} 当前状态为“{registry.support_status_label(model.support_status)}”，"
            "暂不开放型号专属维修指导。你可以查询通用使用说明或提交售后工单。"
        )
        return model, None, direct

    category = _detect_category(db, content, model, fault_category)
    if model and category:
        check = capabilities.check_category(db, model, category)
        if not check["supported"]:
            return (
                model,
                None,
                check.get("message", "该型号尚未验证支持此类故障，建议提交售后工单。"),
            )
    if model and not category and any(word in content for word in GENERIC_TROUBLE_WORDS):
        return (
            model,
            None,
            "请补充具体现象或面板提示，例如卡纸/不进纸、墨盒/墨水、打印质量、无线连接、"
            "无法开机，或直接输入错误码（如 E4、E03）。",
        )

    outcome = printer_rag_service.retrieve(
        db,
        content,
        model=model,
        brand_code=None,
        region=model.region if model else "CN",
        fault_category=category,
        channel="assistant",
        user_id=session.user_id,
    )
    return model, outcome, None


@router.post("/sessions")
def create_session(
    data: AssistantSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    model_id = data.model_id or _default_model(db, current_user)
    if model_id and not _model(db, model_id):
        raise HTTPException(status_code=400, detail="型号不存在")
    session = PrinterChatSession(
        user_id=current_user.id,
        model_id=model_id,
        title=data.title or "新的咨询",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_payload(session)


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = (
        db.query(PrinterChatSession)
        .filter(PrinterChatSession.user_id == current_user.id)
        .order_by(PrinterChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for session in sessions:
        payload = session_payload(session)
        count = (
            db.query(PrinterChatMessage).filter(PrinterChatMessage.session_id == session.id).count()
        )
        last = (
            db.query(PrinterChatMessage)
            .filter(PrinterChatMessage.session_id == session.id)
            .order_by(PrinterChatMessage.id.desc())
            .first()
        )
        payload["message_count"] = count
        payload["last_message"] = last.content[:80] if last else None
        result.append(payload)
    return result


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    messages = (
        db.query(PrinterChatMessage)
        .filter(PrinterChatMessage.session_id == session.id)
        .order_by(PrinterChatMessage.id)
        .all()
    )
    payload = session_payload(session)
    payload["model"] = _model_summary(db, session.model_id)
    payload["messages"] = [message_payload(message) for message in messages]
    return payload


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    db.query(PrinterChatMessage).filter(PrinterChatMessage.session_id == session.id).delete()
    db.delete(session)
    db.commit()
    return {"message": "已删除"}


def _model_summary(db: Session, model_id: str | None) -> dict | None:
    if not model_id:
        return None
    model = _model(db, model_id)
    if not model:
        return None
    from app.api.products import model_payload

    return model_payload(db, model)


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    data: AssistantMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息不能为空")

    _save_message(db, session, "user", content)
    history = _history(db, session.id)
    model, outcome, direct = _prepare(db, session, content, data.fault_category)
    if direct is not None:
        answer = direct
        sources: list[dict] = []
        evidence_sufficient = False
        intent = "clarification"
    else:
        result = printer_rag_service.generate_answer(
            db, content, outcome or {}, model=model, history=history
        )
        answer = result["answer"]
        sources = printer_rag_service.summarize_sources(result["sources"])
        evidence_sufficient = result["evidence_sufficient"]
        intent = result["intent"]

    if session.title == "新的咨询":
        session.title = content[:24] or "新的咨询"
    _save_message(db, session, "assistant", answer, sources, intent)
    if model:
        session.model_id = model.model_id
    db.commit()

    return {
        "session_id": session.id,
        "message": {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "intent": intent,
            "evidence_sufficient": evidence_sufficient,
        },
        "model_id": session.model_id,
    }


@router.post("/sessions/{session_id}/messages/stream")
def stream_message(
    session_id: int,
    data: AssistantMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息不能为空")

    _save_message(db, session, "user", content)
    history = _history(db, session.id)
    model, outcome, direct = _prepare(db, session, content, data.fault_category)

    def generate():
        full_answer = ""
        sources: list[dict] = []
        intent = "clarification"
        try:
            if direct is not None:
                intent = "clarification"
                full_answer = direct
                yield f"data: {json.dumps({'type': 'meta', 'sources': [], 'evidence_sufficient': False, 'intent': intent}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'answer', 'content': direct}, ensure_ascii=False)}\n\n"
            else:
                for chunk in printer_rag_service.generate_answer_stream(
                    db, content, outcome or {}, model=model, history=history
                ):
                    if chunk.get("type") == "meta":
                        sources = printer_rag_service.summarize_sources(chunk.get("sources") or [])
                        intent = chunk.get("intent") or intent
                        chunk = {**chunk, "sources": sources}
                    if chunk.get("type") == "answer":
                        full_answer += chunk.get("content", "")
                    if chunk.get("type") == "done":
                        continue
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if full_answer:
                if session.title == "新的咨询":
                    session.title = content[:24] or "新的咨询"
                if model:
                    session.model_id = model.model_id
                _save_message(db, session, "assistant", full_answer, sources, intent)
                db.commit()
            yield "data: [DONE]\n\n"
        except Exception as exc:
            db.rollback()
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/suggestions")
def suggestions(
    model_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(RepairKnowledge).filter(RepairKnowledge.review_status.in_(REVIEWED))
    if model_id:
        query = query.filter(RepairKnowledge.model_scope.like(f"%{model_id}%"))
    items = query.order_by(RepairKnowledge.fault_category, RepairKnowledge.id).limit(8).all()
    if not items:
        return {
            "items": [
                "我的打印机显示错误码，应该怎么处理？",
                "打印机卡纸了，如何安全取出纸张？",
                "打印出来有断线或条纹怎么办？",
                "打印机无法连接 Wi-Fi 怎么排查？",
            ]
        }
    return {"items": [f"{item.symptom or item.title}（怎么办？）"[:60] for item in items]}


@router.post("/feedback")
def submit_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = UserFeedback(
        user_id=current_user.id,
        channel=data.channel,
        reference_id=data.reference_id,
        rating=max(1, min(5, data.rating)),
        resolved=data.resolved,
        comment=data.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {"id": feedback.id, "message": "感谢反馈"}
