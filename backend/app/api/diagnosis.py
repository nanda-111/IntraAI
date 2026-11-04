"""故障诊断 API：会话、症状提交、步骤反馈与状态查询。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.domains.printer.fault_taxonomy import category_label
from app.models.diagnosis import DiagnosisSession, DiagnosisStep
from app.models.printer_brand import ProductModel
from app.models.user import User
from app.schemas.diagnosis import (
    CloseSession,
    ConfirmModel,
    DiagnosisCreate,
    DiagnosisMessage,
    StepResultSubmit,
)
from app.services import diagnosis_service

router = APIRouter(prefix="/api/diagnosis", tags=["故障诊断"])


def _get_session(db: Session, session_id: int, user: User) -> DiagnosisSession:
    session = db.query(DiagnosisSession).filter(DiagnosisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="诊断会话不存在")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该诊断")
    return session


@router.post("/sessions")
def create_session(
    data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.fault_category:
        from app.domains.printer.fault_taxonomy import FAULT_CATEGORIES

        if data.fault_category not in FAULT_CATEGORIES:
            raise HTTPException(status_code=400, detail="无效的故障类别")
    try:
        session = diagnosis_service.create_session(
            db,
            current_user,
            model_id=data.model_id,
            brand_code=data.brand_code,
            symptom=data.symptom,
            region=data.region,
            fault_category=data.fault_category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return diagnosis_service.build_payload(db, session)


@router.get("/sessions")
def list_sessions(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = diagnosis_service.list_sessions(db, current_user, limit=limit)
    result = []
    for session in sessions:
        model = (
            db.query(ProductModel).filter(ProductModel.model_id == session.model_id).first()
            if session.model_id
            else None
        )
        step_count = (
            db.query(DiagnosisStep).filter(DiagnosisStep.diagnosis_id == session.id).count()
        )
        result.append(
            {
                "id": session.id,
                "session_id": session.diagnosis_uid,
                "status": session.status,
                "model_id": session.model_id,
                "model_name": model.name if model else None,
                "brand_code": session.brand_code,
                "fault_category": session.fault_category,
                "fault_category_label": category_label(session.fault_category),
                "symptom": (session.symptom or "")[:120],
                "step_count": step_count,
                "resolved": session.resolved,
                "escalation_required": session.escalation_required,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            }
        )
    return result


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    return diagnosis_service.build_payload(db, session)


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    data: DiagnosisMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    try:
        diagnosis_service.process_message(db, session, current_user, data.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return diagnosis_service.build_payload(db, session)


@router.post("/sessions/{session_id}/steps/{step_id}/result")
def submit_step_result(
    session_id: int,
    step_id: int,
    data: StepResultSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    try:
        diagnosis_service.submit_step_result(db, session, step_id, data.result, data.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return diagnosis_service.build_payload(db, session)


@router.post("/sessions/{session_id}/model")
def confirm_model(
    session_id: int,
    data: ConfirmModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    try:
        diagnosis_service.set_model(db, session, current_user, data.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return diagnosis_service.build_payload(db, session)


@router.post("/sessions/{session_id}/close")
def close_session(
    session_id: int,
    data: CloseSession,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    diagnosis_service.close_session(db, session, data.resolved, data.note)
    return diagnosis_service.build_payload(db, session)


@router.get("/sessions/{session_id}/summary")
def get_summary(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = _get_session(db, session_id, current_user)
    return {
        "session_id": session.diagnosis_uid,
        "summary": session.summary or diagnosis_service.build_summary(db, session),
        "steps": diagnosis_service.build_payload(db, session)["steps"],
        "sources": session.evidence or [],
        "escalation_required": session.escalation_required,
        "resolved": session.resolved,
    }
