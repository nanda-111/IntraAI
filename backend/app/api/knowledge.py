"""知识中心 API（用户端只读，仅展示已审核/已发布知识）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.printer import registry
from app.models.printer_brand import ProductModel
from app.models.repair_knowledge import RepairKnowledge
from app.services.knowledge_review import knowledge_payload

router = APIRouter(prefix="/api/knowledge", tags=["知识中心"])

REVIEWED = ("approved", "published")


@router.get("")
def list_knowledge(
    brand: str | None = Query(None),
    model_id: str | None = Query(None),
    fault_category: str | None = Query(None),
    fault_code: str | None = Query(None),
    region: str | None = Query(None),
    q: str | None = Query(None),
    source_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(RepairKnowledge).filter(RepairKnowledge.review_status.in_(REVIEWED))
    if brand:
        query = query.filter(RepairKnowledge.brand_code == brand.upper())
    if fault_category:
        query = query.filter(RepairKnowledge.fault_category == fault_category)
    if fault_code:
        query = query.filter(RepairKnowledge.fault_code == fault_code)
    if region:
        query = query.filter(RepairKnowledge.region_scope.in_([region, "ALL", "*"]))
    if source_type:
        query = query.filter(RepairKnowledge.source_type == source_type)
    if q:
        like = f"%{q}%"
        query = query.filter(
            RepairKnowledge.title.like(like)
            | RepairKnowledge.symptom.like(like)
            | RepairKnowledge.fault_code.like(like)
        )

    items = query.order_by(RepairKnowledge.updated_at.desc()).all()
    if model_id:
        model = db.query(ProductModel).filter(ProductModel.model_id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="型号不存在")
        items = [item for item in items if registry.model_scope_matches(model, item.model_scope)]

    total = len(items)
    start = (page - 1) * size
    page_items = items[start : start + size]
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            knowledge_payload(db, item, detail=False) | {"snippet": (item.symptom or "")[:180]}
            for item in page_items
        ],
    }


@router.get("/{doc_id}")
def get_knowledge(doc_id: str, db: Session = Depends(get_db)):
    item = (
        db.query(RepairKnowledge)
        .filter(RepairKnowledge.doc_id == doc_id, RepairKnowledge.review_status.in_(REVIEWED))
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="知识不存在或尚未发布")
    return knowledge_payload(db, item)
