"""运营驾驶舱、系统配置、审计与检索日志 API。"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import effective_role, get_staff, get_system_admin
from app.core.config import settings
from app.core.database import get_db
from app.domains.printer.fault_taxonomy import FAULT_CATEGORIES, category_label
from app.models.audit import AuditLog
from app.models.chat_session import PrinterChatSession, RetrievalLog
from app.models.diagnosis import DiagnosisSession
from app.models.evaluation import EvalRun
from app.models.printer_brand import PrinterBrand, ProductModel
from app.models.repair_knowledge import KnowledgeSource, RepairKnowledge
from app.models.service_ticket import ServiceTicket
from app.models.user import User
from app.services import printer_rag_service
from app.services.ticket_service import TICKET_STATUSES

router = APIRouter(prefix="/api/admin", tags=["管理端-运营"])


@router.get("/dashboard")
def dashboard(
    brand: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff),
):
    brand_filter = brand.upper() if brand else None

    model_query = db.query(ProductModel)
    if brand_filter:
        brand_row = db.query(PrinterBrand).filter(PrinterBrand.brand_code == brand_filter).first()
        if brand_row:
            model_query = model_query.filter(ProductModel.brand_id == brand_row.id)
    models = model_query.all()
    model_ids = [model.model_id for model in models]

    knowledge_query = db.query(RepairKnowledge)
    if brand_filter:
        knowledge_query = knowledge_query.filter(RepairKnowledge.brand_code == brand_filter)
    knowledge = knowledge_query.all()
    status_counts = Counter(item.review_status for item in knowledge)

    diagnosis_query = db.query(DiagnosisSession)
    if brand_filter:
        diagnosis_query = diagnosis_query.filter(DiagnosisSession.brand_code == brand_filter)
    diagnoses = diagnosis_query.all()
    resolved_count = sum(1 for item in diagnoses if item.resolved or item.status == "RESOLVED")
    diagnosis_total = len(diagnoses)
    fault_distribution = Counter(item.fault_category for item in diagnoses if item.fault_category)

    ticket_query = db.query(ServiceTicket)
    if brand_filter:
        ticket_query = ticket_query.filter(ServiceTicket.brand_code == brand_filter)
    tickets = ticket_query.all()
    ticket_status = Counter(ticket.status for ticket in tickets)
    open_statuses = {"pending", "assigned", "processing", "waiting_user", "escalated"}
    open_tickets = sum(count for status, count in ticket_status.items() if status in open_statuses)

    brands = db.query(PrinterBrand).order_by(PrinterBrand.id).all()
    brand_coverage = []
    for brand_item in brands:
        brand_models = [m for m in models if m.brand_id == brand_item.id]
        brand_knowledge = [k for k in knowledge if k.brand_code == brand_item.brand_code]
        brand_coverage.append(
            {
                "brand_code": brand_item.brand_code,
                "brand_name": brand_item.name,
                "model_count": len(brand_models),
                "active_model_count": sum(1 for m in brand_models if m.support_status == "active"),
                "knowledge_count": len(brand_knowledge),
                "published_count": sum(
                    1 for k in brand_knowledge if k.review_status in {"approved", "published"}
                ),
            }
        )

    recent_diagnoses = sorted(
        diagnoses, key=lambda item: item.updated_at or item.created_at, reverse=True
    )[:5]
    recent_tickets = sorted(
        tickets, key=lambda item: item.updated_at or item.created_at, reverse=True
    )[:5]
    latest_eval = db.query(EvalRun).order_by(EvalRun.id.desc()).first()

    return {
        "users": {
            "total": db.query(User).count(),
            "staff": db.query(User)
            .filter(
                (User.is_admin.is_(True))
                | (User.role.in_(["agent", "knowledge_admin", "system_admin"]))
            )
            .count(),
        },
        "models": {
            "total": len(models),
            "active": sum(1 for model in models if model.support_status == "active"),
            "pilot": sum(1 for model in models if model.support_status == "pilot"),
            "active_model_ids": [m.model_id for m in models if m.support_status == "active"],
        },
        "knowledge": {
            "total": len(knowledge),
            "by_status": dict(status_counts),
            "pending_review": status_counts.get("pending", 0),
            "published": status_counts.get("published", 0),
            "official_sources": db.query(KnowledgeSource)
            .filter(KnowledgeSource.authority_level == "A")
            .count(),
        },
        "diagnosis": {
            "total": diagnosis_total,
            "resolved": resolved_count,
            "resolution_rate": round(resolved_count / diagnosis_total, 4)
            if diagnosis_total
            else 0.0,
            "escalated": sum(1 for item in diagnoses if item.status == "ESCALATED"),
            "active": sum(
                1
                for item in diagnoses
                if not item.closed_at and item.status not in {"CLOSED", "CANCELLED"}
            ),
        },
        "tickets": {
            "total": len(tickets),
            "open": open_tickets,
            "by_status": dict(ticket_status),
            "labels": TICKET_STATUSES,
        },
        "fault_distribution": [
            {
                "category": category,
                "label": category_label(category),
                "count": count,
            }
            for category, count in fault_distribution.most_common()
        ],
        "brand_coverage": brand_coverage,
        "chat": {
            "sessions": db.query(PrinterChatSession).count(),
        },
        "evaluation": {
            "latest_run": {
                "id": latest_eval.id,
                "status": latest_eval.status,
                "metrics": latest_eval.metrics or {},
                "finished_at": latest_eval.finished_at.isoformat()
                if latest_eval.finished_at
                else None,
            }
            if latest_eval
            else None
        },
        "recent_diagnoses": [
            {
                "id": item.id,
                "session_id": item.diagnosis_uid,
                "model_id": item.model_id,
                "status": item.status,
                "fault_category": item.fault_category,
                "fault_category_label": category_label(item.fault_category),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in recent_diagnoses
        ],
        "recent_tickets": [
            {
                "id": ticket.id,
                "ticket_no": ticket.ticket_no,
                "title": ticket.title,
                "status": ticket.status,
                "status_label": TICKET_STATUSES.get(ticket.status, ticket.status),
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
            }
            for ticket in recent_tickets
        ],
        "support_scope_note": f"当前支持型号 {len([m for m in models if m.support_status == 'active'])} 个"
        if model_ids
        else "尚未配置支持型号",
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_system_admin)):
    return {
        "llm": {
            "base_url": settings.OPENAI_BASE_URL,
            "model": settings.OPENAI_MODEL,
            "api_key_configured": bool(settings.OPENAI_API_KEY),
        },
        "embedding": {"model": "shibing624/text2vec-base-chinese"},
        "reranker": {"model": settings.RERANK_MODEL},
        "storage": {
            "upload_dir": settings.UPLOAD_DIR,
            "chroma_dir": settings.CHROMA_DIR,
        },
        "index_status": printer_rag_service.index_status(),
        "retrieval": {
            "collections": list(printer_rag_service.COLLECTION_BY_SOURCE.values()),
            "review_required": list(printer_rag_service.REVIEW_OK),
        },
        "audit": {
            "recent_actions": db.query(AuditLog).count(),
        },
        "roles": ["user", "agent", "knowledge_admin", "system_admin"],
        "note": "密钥仅从环境变量读取，不在前端展示或写入数据库。",
    }


@router.get("/audit-logs")
def audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_system_admin),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action.like(f"%{action}%"))
    total = query.count()
    logs = query.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size).all()
    operator_ids = {log.operator_id for log in logs if log.operator_id}
    operators = {
        user.id: user.username for user in db.query(User).filter(User.id.in_(operator_ids)).all()
    }
    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "operator": operators.get(log.operator_id, "系统"),
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "before_value": log.before_value,
                "after_value": log.after_value,
                "reason": log.reason,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/retrieval-logs")
def retrieval_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    channel: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff),
):
    query = db.query(RetrievalLog)
    if channel:
        query = query.filter(RetrievalLog.channel == channel)
    total = query.count()
    logs = query.order_by(RetrievalLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "items": [
            {
                "id": log.id,
                "channel": log.channel,
                "model_id": log.model_id,
                "query": log.query,
                "vector_candidates": log.vector_candidates,
                "bm25_candidates": log.bm25_candidates,
                "evidence_passed": log.evidence_passed,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/fault-categories")
def fault_categories(current_user: User = Depends(get_staff)):
    return [
        {"code": code, "label": meta["label"], "description": meta["description"]}
        for code, meta in FAULT_CATEGORIES.items()
    ]


@router.get("/me/role")
def my_role(current_user: User = Depends(get_staff)):
    return {"role": effective_role(current_user), "user_id": current_user.id}
