"""管理端知识运营：来源登记、文档导入、审核发布与索引管理。"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_knowledge_manager
from app.core.database import get_db
from app.domains.printer.fault_taxonomy import FAULT_CATEGORIES, category_label
from app.models.repair_knowledge import KnowledgeDocument, KnowledgeSource, RepairKnowledge
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeUpdate,
    ReviewRequest,
    SourceCreate,
    SourceUpdate,
)
from app.services import knowledge_ingestion, knowledge_review, printer_rag_service
from app.services.audit_service import log_action

router = APIRouter(
    prefix="/api/admin/knowledge",
    tags=["管理端-知识运营"],
    dependencies=[Depends(get_knowledge_manager)],
)


def source_payload(db: Session, source: KnowledgeSource) -> dict:
    doc_count = db.query(KnowledgeDocument).filter(KnowledgeDocument.source_id == source.id).count()
    knowledge_count = (
        db.query(RepairKnowledge).filter(RepairKnowledge.source_id == source.id).count()
    )
    return {
        "id": source.id,
        "source_key": source.source_key,
        "title": source.title,
        "url": source.url,
        "source_type": source.source_type,
        "authority_level": source.authority_level,
        "brand_code": source.brand_code,
        "model_scope": source.model_scope,
        "region_scope": source.region_scope,
        "version": source.version,
        "license_note": source.license_note,
        "verified_status": source.verified_status,
        "fetched_at": source.fetched_at.isoformat() if source.fetched_at else None,
        "document_count": doc_count,
        "knowledge_count": knowledge_count,
        "created_at": source.created_at.isoformat() if source.created_at else None,
    }


def document_payload(doc: KnowledgeDocument) -> dict:
    return {
        "id": doc.id,
        "source_id": doc.source_id,
        "title": doc.title,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "parse_status": doc.parse_status,
        "parse_error": doc.parse_error,
        "chunk_count": doc.chunk_count,
        "checksum": doc.checksum,
        "index_version": doc.index_version,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(KnowledgeSource).order_by(KnowledgeSource.id.desc()).all()
    return [source_payload(db, source) for source in sources]


@router.post("/sources")
def create_source(data: SourceCreate, db: Session = Depends(get_db)):
    key = data.source_key or f"src_{uuid.uuid4().hex[:10]}"
    if db.query(KnowledgeSource).filter(KnowledgeSource.source_key == key).first():
        raise HTTPException(status_code=400, detail="来源标识已存在")
    if data.authority_level not in {"A", "B", "C", "D"}:
        raise HTTPException(status_code=400, detail="无效的来源等级")
    source = KnowledgeSource(
        source_key=key,
        title=data.title,
        url=data.url,
        source_type=data.source_type,
        authority_level=data.authority_level,
        brand_code=data.brand_code.upper() if data.brand_code else None,
        model_scope=data.model_scope,
        region_scope=data.region_scope,
        version=data.version,
        license_note=data.license_note,
        verified_status=data.verified_status,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source_payload(db, source)


@router.put("/sources/{source_id}")
def update_source(source_id: int, data: SourceUpdate, db: Session = Depends(get_db)):
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    for field in (
        "title",
        "url",
        "source_type",
        "authority_level",
        "model_scope",
        "region_scope",
        "version",
        "license_note",
        "verified_status",
    ):
        value = getattr(data, field)
        if value is not None:
            setattr(source, field, value)
    if data.brand_code is not None:
        source.brand_code = data.brand_code.upper() if data.brand_code else None
    db.commit()
    db.refresh(source)
    return source_payload(db, source)


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    used = db.query(RepairKnowledge).filter(RepairKnowledge.source_id == source_id).count()
    if used:
        raise HTTPException(status_code=400, detail="该来源下仍有知识条目，不能删除")
    db.delete(source)
    db.commit()
    return {"message": "已删除"}


@router.post("/import")
async def import_file(
    file: UploadFile = File(...),
    source_id: int = Form(...),
    brand_code: str = Form(...),
    model_scope: str = Form(...),
    region_scope: str = Form("CN"),
    series: str | None = Form(None),
    fault_category: str = Form("other"),
    fault_code: str | None = Form(None),
    code_system: str | None = Form(None),
    source_type: str | None = Form(None),
    authority_level: str | None = Form(None),
    risk_level: str = Form("L1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    if fault_category not in FAULT_CATEGORIES:
        raise HTTPException(status_code=400, detail="无效的故障类别")
    content = await file.read()
    try:
        result = knowledge_ingestion.import_file(
            db,
            source=source,
            filename=file.filename or "upload",
            content=content,
            brand_code=brand_code,
            model_scope=model_scope,
            region_scope=region_scope,
            series=series,
            fault_category=fault_category,
            fault_code=fault_code,
            code_system=code_system,
            source_type=source_type,
            authority_level=authority_level,
            risk_level=risk_level,
            uploaded_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_action(
        db,
        current_user,
        "knowledge.import",
        "knowledge_document",
        result.get("document_id"),
        after={"file": file.filename, "created": result.get("created")},
    )
    return result


@router.get("/documents")
def list_documents(
    source_id: int | None = Query(None),
    parse_status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgeDocument)
    if source_id:
        query = query.filter(KnowledgeDocument.source_id == source_id)
    if parse_status:
        query = query.filter(KnowledgeDocument.parse_status == parse_status)
    docs = query.order_by(KnowledgeDocument.id.desc()).limit(200).all()
    return [document_payload(doc) for doc in docs]


@router.get("/index-status")
def index_status():
    return printer_rag_service.index_status()


@router.post("/reindex")
def reindex(db: Session = Depends(get_db), current_user: User = Depends(get_knowledge_manager)):
    result = printer_rag_service.reindex_all(db)
    log_action(db, current_user, "knowledge.reindex", "repair_knowledge", None, after=result)
    return result


@router.get("")
def list_knowledge(
    status: str | None = Query(None),
    brand: str | None = Query(None),
    model_id: str | None = Query(None),
    fault_category: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(RepairKnowledge)
    if status:
        query = query.filter(RepairKnowledge.review_status == status)
    if brand:
        query = query.filter(RepairKnowledge.brand_code == brand.upper())
    if model_id:
        query = query.filter(RepairKnowledge.model_scope.like(f"%{model_id}%"))
    if fault_category:
        query = query.filter(RepairKnowledge.fault_category == fault_category)
    if q:
        like = f"%{q}%"
        query = query.filter(RepairKnowledge.title.like(like) | RepairKnowledge.symptom.like(like))
    total = query.count()
    items = (
        query.order_by(RepairKnowledge.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [knowledge_review.knowledge_payload(db, item) for item in items],
    }


@router.post("")
def create_knowledge(
    data: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    try:
        item = knowledge_ingestion.create_knowledge_direct(db, data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(item)
    log_action(
        db,
        current_user,
        "knowledge.create",
        "repair_knowledge",
        item.doc_id,
        after={"title": item.title},
    )
    return knowledge_review.knowledge_payload(db, item)


@router.get("/{doc_id}")
def get_knowledge(doc_id: str, db: Session = Depends(get_db)):
    item = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id == doc_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识不存在")
    return knowledge_review.knowledge_payload(db, item)


@router.put("/{doc_id}")
def update_knowledge(
    doc_id: str,
    data: KnowledgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    item = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id == doc_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识不存在")
    payload = data.model_dump(exclude_unset=True)
    if "fault_category" in payload and payload["fault_category"] not in FAULT_CATEGORIES:
        raise HTTPException(status_code=400, detail="无效的故障类别")
    snapshot = {
        field: getattr(item, field)
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
        )
    }
    item.version_history = (list(item.version_history or []) + [snapshot])[-10:]
    for field, value in payload.items():
        if field == "brand_code" and value:
            value = value.upper()
        setattr(item, field, value)
    item.content_hash = knowledge_ingestion._sha256_text(
        knowledge_ingestion._knowledge_signature(item)
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    if item.review_status == "published":
        printer_rag_service.index_knowledge(db, item)
        db.commit()
    log_action(
        db,
        current_user,
        "knowledge.update",
        "repair_knowledge",
        item.doc_id,
        after=payload,
    )
    return knowledge_review.knowledge_payload(db, item)


@router.delete("/{doc_id}")
def delete_knowledge(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    item = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id == doc_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识不存在")
    printer_rag_service.remove_from_index(item)
    log_action(
        db,
        current_user,
        "knowledge.delete",
        "repair_knowledge",
        doc_id,
        before={"title": item.title},
    )
    db.delete(item)
    db.commit()
    return {"message": "已删除"}


@router.post("/{doc_id}/review")
def review_knowledge(
    doc_id: str,
    data: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_knowledge_manager),
):
    item = db.query(RepairKnowledge).filter(RepairKnowledge.doc_id == doc_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识不存在")
    try:
        return knowledge_review.review_action(db, item, data.action, current_user, data.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/meta/categories")
def knowledge_meta():
    return {
        "fault_categories": [
            {"code": code, "label": meta["label"]} for code, meta in FAULT_CATEGORIES.items()
        ],
        "review_statuses": ["draft", "pending", "approved", "published", "rejected", "archived"],
        "authority_levels": ["A", "B", "C", "D"],
        "categories_label": {code: category_label(code) for code in FAULT_CATEGORIES},
        "updated_at": datetime.now().isoformat(),
    }
