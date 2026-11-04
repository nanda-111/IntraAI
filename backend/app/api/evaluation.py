"""评测中心 API：数据集、测试问题和评测任务。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_knowledge_manager, get_staff
from app.core.database import get_db
from app.models.evaluation import EvalDataset, EvalItem, EvalRun
from app.models.user import User
from app.schemas.evaluation import DatasetCreate, DatasetUpdate, EvalItemCreate
from app.services import evaluation_service

router = APIRouter(prefix="/api/admin/evaluation", tags=["管理端-评测"])


def dataset_payload(db: Session, dataset: EvalDataset) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "brand_code": dataset.brand_code,
        "model_id": dataset.model_id,
        "category": dataset.category,
        "description": dataset.description,
        "item_count": db.query(EvalItem).filter(EvalItem.dataset_id == dataset.id).count(),
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


def item_payload(item: EvalItem) -> dict:
    return {
        "id": item.id,
        "dataset_id": item.dataset_id,
        "question": item.question,
        "expected_doc_ids": item.expected_doc_ids or [],
        "expected_fault_category": item.expected_fault_category,
        "expected_escalation": str(item.expected_escalation).lower() == "true",
        "notes": item.notes,
    }


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_staff)):
    datasets = db.query(EvalDataset).order_by(EvalDataset.id.desc()).all()
    return [dataset_payload(db, dataset) for dataset in datasets]


@router.post("/datasets")
def create_dataset(
    data: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    dataset = EvalDataset(
        name=data.name,
        brand_code=data.brand_code,
        model_id=data.model_id,
        category=data.category,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset_payload(db, dataset)


@router.put("/datasets/{dataset_id}")
def update_dataset(
    dataset_id: int,
    data: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    for field in ("name", "brand_code", "model_id", "category", "description"):
        value = getattr(data, field)
        if value is not None:
            setattr(dataset, field, value)
    db.commit()
    db.refresh(dataset)
    return dataset_payload(db, dataset)


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    db.query(EvalItem).filter(EvalItem.dataset_id == dataset_id).delete()
    db.delete(dataset)
    db.commit()
    return {"message": "已删除"}


@router.get("/datasets/{dataset_id}/items")
def list_items(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff),
):
    items = db.query(EvalItem).filter(EvalItem.dataset_id == dataset_id).order_by(EvalItem.id).all()
    return [item_payload(item) for item in items]


@router.post("/datasets/{dataset_id}/items")
def create_item(
    dataset_id: int,
    data: EvalItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    item = EvalItem(
        dataset_id=dataset_id,
        question=data.question,
        expected_doc_ids=data.expected_doc_ids,
        expected_fault_category=data.expected_fault_category,
        expected_escalation="true" if data.expected_escalation else "false",
        notes=data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_payload(item)


@router.delete("/datasets/{dataset_id}/items/{item_id}")
def delete_item(
    dataset_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    item = (
        db.query(EvalItem).filter(EvalItem.id == item_id, EvalItem.dataset_id == dataset_id).first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="测试问题不存在")
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


@router.post("/datasets/{dataset_id}/run")
def run_evaluation(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    dataset = db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    item_count = db.query(EvalItem).filter(EvalItem.dataset_id == dataset_id).count()
    if item_count == 0:
        raise HTTPException(status_code=400, detail="数据集没有测试问题")
    run = evaluation_service.run_dataset(db, dataset, current_user)
    return evaluation_service.run_payload(db, run)


@router.get("/runs")
def list_runs(
    dataset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff),
):
    query = db.query(EvalRun)
    if dataset_id:
        query = query.filter(EvalRun.dataset_id == dataset_id)
    runs = query.order_by(EvalRun.id.desc()).limit(50).all()
    return [evaluation_service.run_payload(db, run) for run in runs]


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff),
):
    run = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="评测任务不存在")
    return evaluation_service.run_payload(db, run)
