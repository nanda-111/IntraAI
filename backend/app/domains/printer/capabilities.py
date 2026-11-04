"""型号能力映射：声明型号已被证据支持的故障类别和代码体系。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.printer import registry
from app.models.printer_brand import ProductModel


def capability_list(db: Session, model_id: str) -> list[dict]:
    return [
        {
            "id": item.id,
            "model_id": item.model_id,
            "fault_category": item.fault_category,
            "code_system": item.code_system,
            "supported_features": item.supported_features or [],
            "source_id": item.source_id,
            "verified_status": item.verified_status,
            "notes": item.notes,
        }
        for item in registry.get_capabilities(db, model_id)
    ]


def check_category(db: Session, model: ProductModel, category: str | None) -> dict:
    """返回能力检查结果，供诊断入口决定是否开放型号专属流程。"""
    if not category:
        return {"supported": False, "reason": "missing_category"}
    if not registry.supports_fault_category(db, model, category):
        return {
            "supported": False,
            "reason": "capability_not_verified",
            "message": "该型号尚未验证支持此类故障的自动诊断，建议使用智能客服或提交工单。",
        }
    return {"supported": True, "reason": "ok"}


def refresh_coverage(db: Session, model: ProductModel, knowledge_count: int) -> None:
    model.knowledge_coverage = knowledge_count
    db.add(model)
