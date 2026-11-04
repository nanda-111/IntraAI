"""故障诊断状态机与编排服务。

状态：MODEL_PENDING → MODEL_CONFIRMED → COLLECTING → RETRIEVING → STEP_READY
→ WAIT_USER_ACTION → RESOLVED / ESCALATED → CLOSED / CANCELLED。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.domains.printer import capabilities, registry
from app.domains.printer.fault_taxonomy import (
    category_label,
    classify_symptom,
    lookup_error_code,
)
from app.domains.printer.safety_policy import (
    EVIDENCE_INSUFFICIENT_NOTICE,
    filter_self_service_steps,
    is_high_risk_request,
    refusal_answer,
)
from app.models.diagnosis import DiagnosisSession, DiagnosisStep, DiagnosisTurn
from app.models.printer_brand import ProductModel
from app.models.user import User
from app.services import printer_rag_service

ACTIVE_STATES = {
    "MODEL_PENDING",
    "MODEL_CONFIRMED",
    "COLLECTING",
    "RETRIEVING",
    "STEP_READY",
    "WAIT_USER_ACTION",
}
RESULT_MAP = {
    "已完成": "done",
    "完成": "done",
    "done": "done",
    "已执行": "done",
    "还是不行": "failed",
    "没解决": "failed",
    "未解决": "failed",
    "failed": "failed",
    "无法执行": "skipped",
    "跳过": "skipped",
    "skipped": "skipped",
}
RESOLVED_WORDS = ("已解决", "解决了", "好了", "恢复正常", "可以打印了", "resolved")
ESCALATE_WORDS = ("转人工", "人工客服", "提交工单", "创建工单", "找客服", "escalate")


def create_session(
    db: Session,
    user: User,
    model_id: str | None = None,
    brand_code: str | None = None,
    symptom: str | None = None,
    region: str = "CN",
    fault_category: str | None = None,
) -> DiagnosisSession:
    session = DiagnosisSession(
        diagnosis_uid=f"diag_{uuid.uuid4().hex[:12]}",
        user_id=user.id,
        model_id=model_id,
        brand_code=brand_code,
        region=region,
        symptom=symptom,
        fault_category=fault_category,
        status="MODEL_PENDING",
        slot_snapshot={
            "region": region,
            "symptom": symptom or "",
            "fault_category": fault_category,
        },
    )
    db.add(session)
    db.flush()

    if model_id:
        model = registry.require_model(db, model_id)
        _attach_model(db, session, model)
        if not registry.is_diagnosis_supported(model):
            _set_state(
                db,
                session,
                "ESCALATED",
                escalation=True,
                message=(
                    f"该型号当前状态为“{registry.support_status_label(model.support_status)}”，"
                    "暂不开放型号专属自动诊断。你可以查询通用资料或提交售后工单。"
                ),
            )
        elif symptom:
            _user_turn(db, session, symptom)
            _process_symptoms(db, session, user, symptom, fault_category)
        else:
            category_hint = (
                f"已记录故障类别“{category_label(fault_category)}”。" if fault_category else ""
            )
            _set_state(
                db,
                session,
                "COLLECTING",
                message=(
                    f"已确认型号 {model.name}。{category_hint}"
                    "请描述故障现象，或输入面板上的错误码/灯态。"
                ),
            )
    else:
        _set_state(
            db,
            session,
            "MODEL_PENDING",
            message="请先告诉我打印机的品牌和具体型号（例如 HP DeskJet 2720、Canon TS5380）。",
        )
    db.commit()
    db.refresh(session)
    return session


def _attach_model(db: Session, session: DiagnosisSession, model: ProductModel) -> None:
    from app.models.printer_brand import PrinterBrand

    brand = (
        db.query(PrinterBrand).filter(PrinterBrand.id == model.brand_id).first()
        if model.brand_id
        else None
    )
    session.model_id = model.model_id
    session.brand_code = brand.brand_code if brand else session.brand_code
    slots = dict(session.slot_snapshot or {})
    slots.update(
        {
            "brand": session.brand_code,
            "model_id": model.model_id,
            "model_name": model.name,
            "series": model.series,
            "region": session.region,
        }
    )
    session.slot_snapshot = slots
    session.status = "MODEL_CONFIRMED"


def _user_turn(db: Session, session: DiagnosisSession, content: str) -> DiagnosisTurn:
    turn = DiagnosisTurn(
        diagnosis_id=session.id,
        role="user",
        content=content,
        state=session.status,
    )
    db.add(turn)
    return turn


def _assistant_turn(
    db: Session, session: DiagnosisSession, content: str, meta: dict | None = None
) -> DiagnosisTurn:
    turn = DiagnosisTurn(
        diagnosis_id=session.id,
        role="assistant",
        content=content,
        state=session.status,
        meta=meta or {},
    )
    db.add(turn)
    return turn


def _set_state(
    db: Session,
    session: DiagnosisSession,
    state: str,
    *,
    message: str | None = None,
    escalation: bool = False,
) -> None:
    session.status = state
    session.escalation_required = escalation or session.escalation_required
    session.updated_at = datetime.now()
    if state in {"RESOLVED", "CLOSED", "CANCELLED"}:
        session.closed_at = datetime.now()
    if message:
        _assistant_turn(db, session, message, {"state": state})


def _process_symptoms(
    db: Session,
    session: DiagnosisSession,
    user: User,
    text: str,
    fault_category: str | None = None,
) -> DiagnosisSession:
    model = registry.require_model(db, session.model_id)
    category = fault_category or classify_symptom(text) or session.fault_category
    code = registry.extract_error_code(text)

    if code and session.brand_code:
        mapped = lookup_error_code(session.brand_code, code)
        if mapped:
            category = mapped["category"]
            session.brand_error_code = mapped["code"]
            session.fault_category = category
    if category:
        session.fault_category = category
    if text:
        session.symptom = text
    slots = dict(session.slot_snapshot or {})
    slots.update(
        {
            "fault_category": session.fault_category,
            "brand_error_code": session.brand_error_code,
            "symptom": session.symptom,
        }
    )
    session.slot_snapshot = slots
    session.status = "RETRIEVING"
    db.add(session)
    db.flush()

    if not category:
        _set_state(
            db,
            session,
            "COLLECTING",
            message=(
                "请补充故障类别或面板提示：例如卡纸/不进纸、墨盒或墨水、打印质量、"
                "无线连接、无法开机，或直接输入错误码。"
            ),
        )
        return session

    capability = capabilities.check_category(db, model, category)
    if not capability["supported"]:
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message=capability.get("message", EVIDENCE_INSUFFICIENT_NOTICE),
        )
        return session

    query = _build_query(session, text)
    outcome = printer_rag_service.retrieve(
        db,
        query,
        model=model,
        brand_code=session.brand_code,
        region=session.region,
        fault_category=category,
        channel="diagnosis",
        user_id=user.id,
    )
    if not outcome["evidence_sufficient"]:
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message=EVIDENCE_INSUFFICIENT_NOTICE,
        )
        return session

    session.evidence = printer_rag_service.summarize_sources(outcome["results"])
    _create_steps(db, session, outcome["results"])
    db.flush()
    _move_to_next_step(db, session)
    return session


def _build_query(session: DiagnosisSession, text: str) -> str:
    parts = [text or session.symptom or ""]
    if session.fault_category:
        parts.append(category_label(session.fault_category))
    if session.brand_error_code:
        parts.append(session.brand_error_code)
    return " ".join(part for part in parts if part).strip()


def _create_steps(db: Session, session: DiagnosisSession, results: list[dict]) -> None:
    existing = db.query(DiagnosisStep).filter(DiagnosisStep.diagnosis_id == session.id).count()
    if existing:
        return
    from app.models.repair_knowledge import RepairKnowledge

    primary_id = results[0]["doc_id"]
    item = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id == primary_id).first()
    if not item:
        return
    steps = filter_self_service_steps(item.steps or [])
    for index, step in enumerate(steps, start=1):
        instruction = step.get("instruction") if isinstance(step, dict) else str(step)
        risk = step.get("risk_level", "L1") if isinstance(step, dict) else "L1"
        expected = step.get("expected_result", "") if isinstance(step, dict) else ""
        db.add(
            DiagnosisStep(
                diagnosis_id=session.id,
                step_no=index,
                instruction=str(instruction),
                risk_level=risk,
                expected_result=str(expected) if expected else "",
                source_doc_id=item.doc_id,
                source_title=item.title,
                source_url=next(
                    (s.get("url") for s in results if s.get("doc_id") == item.doc_id), None
                ),
            )
        )


def _move_to_next_step(db: Session, session: DiagnosisSession) -> None:
    step = (
        db.query(DiagnosisStep)
        .filter(
            DiagnosisStep.diagnosis_id == session.id,
            DiagnosisStep.status == "pending",
        )
        .order_by(DiagnosisStep.step_no)
        .first()
    )
    if step:
        # 保证同一时间只有一条 ready 步骤
        db.query(DiagnosisStep).filter(
            DiagnosisStep.diagnosis_id == session.id,
            DiagnosisStep.status == "ready",
        ).update({"status": "pending"})
        step.status = "ready"
        session.current_step_no = step.step_no
        session.status = "STEP_READY"
        message = (
            f"请执行第 {step.step_no} 步：{step.instruction}\n"
            f"风险等级：{step.risk_level}。完成后请告诉我结果。"
        )
        _assistant_turn(
            db,
            session,
            message,
            {
                "state": "STEP_READY",
                "step_id": step.id,
                "risk_level": step.risk_level,
                "sources": session.evidence,
            },
        )
        session.status = "WAIT_USER_ACTION"
        return

    session.status = "WAIT_USER_ACTION"
    _assistant_turn(
        db,
        session,
        "以上已审核步骤已全部执行。问题是否已经解决？若仍未解决，可以提交售后工单转人工处理。",
        {"state": "WAIT_USER_ACTION", "sources": session.evidence},
    )


def _current_step(db: Session, session: DiagnosisSession) -> DiagnosisStep | None:
    return (
        db.query(DiagnosisStep)
        .filter(
            DiagnosisStep.diagnosis_id == session.id,
            DiagnosisStep.status == "ready",
        )
        .order_by(DiagnosisStep.step_no.desc())
        .first()
    )


def process_message(
    db: Session,
    session: DiagnosisSession,
    user: User,
    text: str,
) -> DiagnosisSession:
    text = (text or "").strip()
    if not text:
        raise ValueError("消息不能为空")
    if session.status in {"CLOSED", "CANCELLED"}:
        raise ValueError("该诊断已结束，请新建诊断会话")

    _user_turn(db, session, text)
    lowered = text.lower()

    if is_high_risk_request(text):
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message=refusal_answer(),
        )
        db.commit()
        db.refresh(session)
        return session

    if any(word in lowered for word in ESCALATE_WORDS):
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message="已为你转接人工处理。你可以在工单中心确认并提交售后工单。",
        )
        db.commit()
        db.refresh(session)
        return session

    # 1. 尚未确认型号：尝试从文本解析
    if not session.model_id:
        brand = registry.detect_brand(text) or session.brand_code
        resolved = registry.resolve_model(db, text=text, brand_code=brand, region=session.region)
        model = resolved.get("model")
        if model and not resolved["requires_confirmation"]:
            _attach_model(db, session, model)
            if not registry.is_diagnosis_supported(model):
                _set_state(
                    db,
                    session,
                    "ESCALATED",
                    escalation=True,
                    message=(
                        f"该型号当前状态为“{registry.support_status_label(model.support_status)}”，"
                        "暂不开放型号专属自动诊断。"
                    ),
                )
            else:
                _process_symptoms(db, session, user, text)
            db.commit()
            db.refresh(session)
            return session

        candidates = resolved.get("candidates") or []
        if candidates:
            names = "、".join(model.name for model in candidates[:4])
            message = f"我识别到多个可能型号：{names}。请确认具体型号后继续。"
        else:
            message = "尚未识别到具体型号。请提供完整型号，例如 HP DeskJet 2720 / Canon TS5380。"
        _set_state(db, session, "MODEL_PENDING", message=message)
        db.commit()
        db.refresh(session)
        return session

    # 2. 已确认型号，处理“已解决”/步骤反馈
    if any(word in lowered for word in RESOLVED_WORDS):
        session.status = "RESOLVED"
        session.resolved = True
        session.closed_at = datetime.now()
        session.summary = build_summary(db, session)
        _assistant_turn(
            db, session, "已记录问题解决。感谢反馈，本次诊断已结束。", {"state": "RESOLVED"}
        )
        db.commit()
        db.refresh(session)
        return session

    current = _current_step(db, session)
    if current and session.status == "WAIT_USER_ACTION":
        result = _detect_result(lowered)
        if result:
            _apply_step_result(db, session, current, result, note=text)
            db.commit()
            db.refresh(session)
            return session

    # 3. 重新收集症状并检索
    _process_symptoms(db, session, user, text)
    db.commit()
    db.refresh(session)
    return session


def _detect_result(lowered: str) -> str | None:
    for phrase, result in RESULT_MAP.items():
        if phrase in lowered:
            return result
    return None


def _apply_step_result(
    db: Session,
    session: DiagnosisSession,
    step: DiagnosisStep,
    result: str,
    note: str | None = None,
) -> None:
    step.status = result
    step.user_result = result
    step.user_note = note
    step.completed_at = datetime.now()
    db.add(step)
    session.updated_at = datetime.now()

    if result == "done":
        _move_to_next_step(db, session)
    elif result == "failed":
        session.status = "COLLECTING"
        _assistant_turn(
            db,
            session,
            "已记录“未解决”。请补充当前现象或面板提示（如错误码、指示灯状态），我会重新检索可用资料。",
            {"state": "COLLECTING"},
        )
    else:
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message="该步骤无法执行。为避免不安全的操作，建议提交售后工单转人工处理。",
        )


def submit_step_result(
    db: Session,
    session: DiagnosisSession,
    step_id: int,
    result: str,
    note: str | None = None,
) -> DiagnosisSession:
    if session.status not in ACTIVE_STATES:
        raise ValueError("当前诊断状态不允许提交步骤结果")
    step = (
        db.query(DiagnosisStep)
        .filter(DiagnosisStep.id == step_id, DiagnosisStep.diagnosis_id == session.id)
        .first()
    )
    if not step:
        raise ValueError("步骤不存在")
    if result not in {"done", "failed", "skipped"}:
        raise ValueError("无效的步骤结果")
    _apply_step_result(db, session, step, result, note)
    db.commit()
    db.refresh(session)
    return session


def set_model(
    db: Session, session: DiagnosisSession, user: User, model_id: str
) -> DiagnosisSession:
    model = registry.require_model(db, model_id)
    _attach_model(db, session, model)
    if not registry.is_diagnosis_supported(model):
        _set_state(
            db,
            session,
            "ESCALATED",
            escalation=True,
            message=(
                f"该型号当前状态为“{registry.support_status_label(model.support_status)}”，"
                "暂不开放型号专属自动诊断。"
            ),
        )
    else:
        _set_state(
            db,
            session,
            "COLLECTING",
            message=f"已确认型号 {model.name}。请描述故障现象或输入错误码/灯态。",
        )
    db.commit()
    db.refresh(session)
    return session


def close_session(
    db: Session, session: DiagnosisSession, resolved: bool, note: str | None = None
) -> DiagnosisSession:
    if session.status in {"CLOSED", "CANCELLED"}:
        return session
    session.status = "RESOLVED" if resolved else "CANCELLED"
    session.resolved = resolved
    session.resolution_note = note
    session.closed_at = datetime.now()
    session.summary = build_summary(db, session)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def build_summary(db: Session, session: DiagnosisSession) -> str:
    model = (
        db.query(ProductModel).filter(ProductModel.model_id == session.model_id).first()
        if session.model_id
        else None
    )
    steps = (
        db.query(DiagnosisStep)
        .filter(DiagnosisStep.diagnosis_id == session.id)
        .order_by(DiagnosisStep.step_no)
        .all()
    )
    executed = [f"{step.step_no}.{step.status}" for step in steps]
    parts = [
        f"型号：{model.name if model else '未确认'}",
        f"故障类别：{category_label(session.fault_category)}",
        f"错误码：{session.brand_error_code or '未提供'}",
        f"现象：{(session.symptom or '')[:200]}",
        f"执行步骤：{'，'.join(executed) if executed else '未执行'}",
        f"结果：{'已解决' if session.resolved else '未解决' if session.closed_at else '进行中'}",
    ]
    return "；".join(parts)


def build_payload(db: Session, session: DiagnosisSession, include_turns: bool = True) -> dict:
    model = (
        db.query(ProductModel).filter(ProductModel.model_id == session.model_id).first()
        if session.model_id
        else None
    )
    steps = (
        db.query(DiagnosisStep)
        .filter(DiagnosisStep.diagnosis_id == session.id)
        .order_by(DiagnosisStep.step_no)
        .all()
    )
    turns = (
        db.query(DiagnosisTurn)
        .filter(DiagnosisTurn.diagnosis_id == session.id)
        .order_by(DiagnosisTurn.created_at, DiagnosisTurn.id)
        .all()
        if include_turns
        else []
    )
    current = next((step for step in steps if step.status == "ready"), None)
    next_question = _next_question(session, current)
    return {
        "id": session.id,
        "session_id": session.diagnosis_uid,
        "status": session.status,
        "diagnosis_state": session.status,
        "product": {
            "brand": session.brand_code,
            "model_id": session.model_id,
            "model_name": model.name if model else None,
            "region": session.region,
            "support_status": model.support_status if model else None,
        },
        "fault": {
            "category": session.fault_category,
            "category_label": category_label(session.fault_category),
            "brand_error_code": session.brand_error_code,
            "confidence": "evidence_supported" if session.evidence else "unconfirmed",
        },
        "current_step": _step_payload(current) if current else None,
        "steps": [_step_payload(step, full=True) for step in steps],
        "sources": session.evidence or [],
        "next_question": next_question,
        "escalation_required": session.escalation_required,
        "resolved": session.resolved,
        "summary": session.summary,
        "turns": [
            {
                "id": turn.id,
                "role": turn.role,
                "content": turn.content,
                "state": turn.state,
                "meta": turn.meta or {},
                "created_at": turn.created_at.isoformat() if turn.created_at else None,
            }
            for turn in turns
        ],
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def _step_payload(step: DiagnosisStep, full: bool = False) -> dict:
    payload = {
        "step_id": step.id,
        "step_no": step.step_no,
        "instruction": step.instruction,
        "risk_level": step.risk_level,
        "expected_result": step.expected_result,
        "status": step.status,
        "source_doc_id": step.source_doc_id,
        "source_title": step.source_title,
        "source_url": step.source_url,
    }
    if full:
        payload.update({"user_result": step.user_result, "user_note": step.user_note})
    return payload


def _next_question(session: DiagnosisSession, current: DiagnosisStep | None) -> str | None:
    if current:
        return "执行后是否恢复正常？请反馈“已完成”或“还是不行”。"
    if session.status == "MODEL_PENDING":
        return "请确认打印机品牌和具体型号。"
    if session.status == "COLLECTING":
        return "请描述故障现象或面板错误码/灯态。"
    if session.status == "WAIT_USER_ACTION":
        return "问题是否已经解决？"
    if session.status == "ESCALATED":
        return "是否提交售后工单转人工处理？"
    return None


def list_sessions(db: Session, user: User, limit: int = 50) -> list[DiagnosisSession]:
    return (
        db.query(DiagnosisSession)
        .filter(DiagnosisSession.user_id == user.id)
        .order_by(DiagnosisSession.updated_at.desc())
        .limit(limit)
        .all()
    )
