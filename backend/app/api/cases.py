"""维修案例管理 API（社区案例与人工分析案例）。"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_knowledge_manager
from app.core.database import get_db
from app.domains.printer.fault_taxonomy import FAULT_CATEGORIES, category_label
from app.models.repair_knowledge import RepairCase
from app.models.user import User
from app.services.audit_service import log_action

router = APIRouter(
    prefix="/api/admin/cases",
    tags=["管理端-维修案例"],
    dependencies=[Depends(get_knowledge_manager)],
)


class CaseCreate(BaseModel):
    raw_brand: str | None = None
    raw_model: str | None = None
    problem_text: str
    fault_label: str | None = None
    repair_outcome: str | None = None
    model_known: str = "unknown"
    credibility: str = "unverified"
    notes: str | None = None
    source_id: int | None = None


class CaseUpdate(BaseModel):
    raw_brand: str | None = None
    raw_model: str | None = None
    problem_text: str | None = None
    fault_label: str | None = None
    repair_outcome: str | None = None
    model_known: str | None = None
    credibility: str | None = None
    notes: str | None = None


def case_payload(case: RepairCase) -> dict:
    return {
        "id": case.id,
        "case_id": case.case_id,
        "raw_brand": case.raw_brand,
        "raw_model": case.raw_model,
        "problem_text": case.problem_text,
        "fault_label": case.fault_label,
        "fault_label_text": category_label(case.fault_label),
        "repair_outcome": case.repair_outcome,
        "model_known": case.model_known,
        "credibility": case.credibility,
        "notes": case.notes,
        "source_id": case.source_id,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "disclaimer": "社区案例，不是官方维修步骤",
    }


@router.get("")
def list_cases(
    brand: str | None = Query(None),
    model_known: str | None = Query(None),
    fault_label: str | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(RepairCase)
    if brand:
        query = query.filter(RepairCase.raw_brand.like(f"%{brand}%"))
    if model_known:
        query = query.filter(RepairCase.model_known == model_known)
    if fault_label:
        query = query.filter(RepairCase.fault_label == fault_label)
    if q:
        like = f"%{q}%"
        query = query.filter(RepairCase.problem_text.like(like))
    cases = query.order_by(RepairCase.id.desc()).limit(200).all()
    return [case_payload(case) for case in cases]


@router.post("")
def create_case(data: CaseCreate, db: Session = Depends(get_db)):
    if data.fault_label and data.fault_label not in FAULT_CATEGORIES:
        raise HTTPException(status_code=400, detail="无效的故障类别")
    case = RepairCase(
        case_id=f"case_{uuid.uuid4().hex[:10]}",
        source_id=data.source_id,
        raw_brand=data.raw_brand,
        raw_model=data.raw_model,
        problem_text=data.problem_text,
        fault_label=data.fault_label,
        repair_outcome=data.repair_outcome,
        model_known=data.model_known if data.model_known in {"known", "unknown"} else "unknown",
        credibility=data.credibility,
        notes=data.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case_payload(case)


@router.post("/import")
async def import_cases(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    content = (await file.read()).decode("utf-8", errors="ignore")
    records = []
    try:
        if (file.filename or "").endswith(".jsonl"):
            records = [json.loads(line) for line in content.splitlines() if line.strip()]
        else:
            parsed = json.loads(content)
            records = parsed if isinstance(parsed, list) else [parsed]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {exc}") from exc

    created = 0
    for record in records:
        if not isinstance(record, dict) or not record.get("problem_text"):
            continue
        label = record.get("fault_label")
        if label and label not in FAULT_CATEGORIES:
            label = "other"
        case = RepairCase(
            case_id=record.get("case_id") or f"case_{uuid.uuid4().hex[:10]}",
            source_id=record.get("source_id"),
            raw_brand=record.get("raw_brand"),
            raw_model=record.get("raw_model"),
            problem_text=record["problem_text"],
            fault_label=label,
            repair_outcome=record.get("repair_outcome"),
            model_known=record.get("model_known", "unknown"),
            credibility=record.get("credibility", "unverified"),
            notes=record.get("notes"),
        )
        db.add(case)
        created += 1
    log_action(
        db,
        current_user,
        "cases.import",
        "repair_case",
        None,
        after={"file": file.filename, "created": created},
    )
    db.commit()
    return {"created": created, "total": len(records)}


@router.put("/{case_id}")
def update_case(
    case_id: str,
    data: CaseUpdate,
    db: Session = Depends(get_db),
):
    case = db.query(RepairCase).filter(RepairCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")
    for field in (
        "raw_brand",
        "raw_model",
        "problem_text",
        "fault_label",
        "repair_outcome",
        "model_known",
        "credibility",
        "notes",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case_payload(case)


@router.delete("/{case_id}")
def delete_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RepairCase).filter(RepairCase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案例不存在")
    db.delete(case)
    db.commit()
    return {"message": "已删除"}
