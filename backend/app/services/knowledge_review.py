"""知识审核、发布与索引同步。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domains.printer.fault_taxonomy import category_label
from app.models.repair_knowledge import KnowledgeSource, RepairKnowledge
from app.models.user import User
from app.services import printer_rag_service
from app.services.audit_service import log_action

REVIEW_ACTIONS = {"approve", "reject", "publish", "archive", "rollback"}


def validate_for_publish(item: RepairKnowledge) -> list[str]:
    issues = []
    if not item.model_scope:
        issues.append("缺少适用范围 model_scope")
    if not item.fault_category:
        issues.append("缺少故障类别")
    if not item.steps:
        issues.append("缺少结构化操作步骤，不能发布为可检索维修知识")
    if not item.safety_warnings:
        issues.append("缺少安全提示")
    if item.risk_level == "L3":
        issues.append("高风险知识不允许进入用户自助检索")
    if not item.source_id:
        issues.append("缺少来源来源登记")
    return issues


def review_action(
    db: Session,
    item: RepairKnowledge,
    action: str,
    reviewer: User,
    note: str | None = None,
) -> dict:
    if action not in REVIEW_ACTIONS:
        raise ValueError("不支持的审核动作")

    before = item.review_status
    if action == "approve":
        issues = validate_for_publish(item)
        if issues:
            raise ValueError("；".join(issues))
        item.review_status = "approved"
        item.reviewer_id = reviewer.id
        item.reviewed_at = datetime.now()
        item.review_note = note
    elif action == "reject":
        item.review_status = "rejected"
        item.reviewer_id = reviewer.id
        item.reviewed_at = datetime.now()
        item.review_note = note
        printer_rag_service.remove_from_index(item)
    elif action == "publish":
        if item.review_status not in {"approved", "published"}:
            raise ValueError("知识必须先审核通过才能发布")
        issues = validate_for_publish(item)
        if issues:
            raise ValueError("；".join(issues))
        item.review_status = "published"
        item.reviewer_id = reviewer.id
        item.reviewed_at = datetime.now()
        item.review_note = note
        db.add(item)
        printer_rag_service.index_knowledge(db, item)
    elif action == "archive":
        item.review_status = "archived"
        item.reviewer_id = reviewer.id
        item.reviewed_at = datetime.now()
        item.review_note = note
        printer_rag_service.remove_from_index(item)
    elif action == "rollback":
        history = list(item.version_history or [])
        if not history:
            raise ValueError("没有可回滚的历史版本")
        snapshot = history.pop()
        for field in (
            "title",
            "symptom",
            "possible_causes",
            "steps",
            "safety_warnings",
            "risk_level",
            "fault_category",
            "fault_code",
            "version",
        ):
            if field in snapshot:
                setattr(item, field, snapshot[field])
        item.version_history = history
        item.review_status = "approved"
        item.review_note = note or "回滚到上一版本"
        printer_rag_service.remove_from_index(item)

    db.add(item)
    log_action(
        db,
        reviewer,
        f"knowledge.{action}",
        "repair_knowledge",
        item.doc_id,
        before={"review_status": before},
        after={"review_status": item.review_status},
        reason=note,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return knowledge_payload(db, item)


def knowledge_payload(db: Session, item: RepairKnowledge, detail: bool = True) -> dict:
    source = (
        db.query(KnowledgeSource).filter(KnowledgeSource.id == item.source_id).first()
        if item.source_id
        else None
    )
    payload = {
        "id": item.id,
        "doc_id": item.doc_id,
        "title": item.title,
        "brand_code": item.brand_code,
        "series": item.series,
        "model_scope": item.model_scope,
        "region_scope": item.region_scope,
        "code_system": item.code_system,
        "fault_category": item.fault_category,
        "fault_category_label": category_label(item.fault_category),
        "fault_code": item.fault_code,
        "source_type": item.source_type,
        "authority_level": item.authority_level,
        "review_status": item.review_status,
        "risk_level": item.risk_level,
        "version": item.version,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "source": {
            "id": source.id,
            "source_key": source.source_key,
            "title": source.title,
            "url": source.url,
            "authority_level": source.authority_level,
        }
        if source
        else None,
    }
    if detail:
        payload.update(
            {
                "symptom": item.symptom,
                "possible_causes": item.possible_causes or [],
                "preconditions": item.preconditions or [],
                "steps": item.steps or [],
                "expected_result": item.expected_result,
                "verification_method": item.verification_method,
                "safety_warnings": item.safety_warnings or [],
                "review_note": item.review_note,
                "index_version": item.index_version,
                "content_hash": item.content_hash,
                "version_history": item.version_history or [],
            }
        )
    return payload
