"""售后工单 API（用户端 + 客服管理端）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_support_staff
from app.core.database import get_db
from app.models.diagnosis import DiagnosisSession
from app.models.service_ticket import ServiceTicket
from app.models.user import User
from app.schemas.ticket import TicketComment, TicketCreate, TicketUpdate, TicketUserClose
from app.services import ticket_service

router = APIRouter(prefix="/api/tickets", tags=["售后工单"])
admin_router = APIRouter(
    prefix="/api/admin/tickets",
    tags=["管理端-工单"],
    dependencies=[Depends(get_support_staff)],
)


def _own_ticket(db: Session, ticket_id: int, user: User) -> ServiceTicket:
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该工单")
    return ticket


@router.post("")
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    diagnosis = None
    if data.diagnosis_id:
        diagnosis = (
            db.query(DiagnosisSession).filter(DiagnosisSession.id == data.diagnosis_id).first()
        )
        if not diagnosis:
            raise HTTPException(status_code=404, detail="诊断记录不存在")
        if diagnosis.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权引用该诊断")
    title = data.title or (
        diagnosis.summary[:80] if diagnosis and diagnosis.summary else "售后工单"
    )
    ticket = ticket_service.create_ticket(
        db,
        current_user,
        title=title,
        summary=data.summary,
        model_id=data.model_id,
        brand_code=data.brand_code,
        contact=data.contact,
        contact_type=data.contact_type,
        fault_category=data.fault_category,
        brand_error_code=data.brand_error_code,
        diagnosis=diagnosis,
        priority=data.priority,
    )
    return ticket_service.ticket_payload(db, ticket)


@router.get("")
def list_tickets(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tickets = ticket_service.list_tickets(db, current_user, status)
    return [ticket_service.ticket_payload(db, ticket) for ticket in tickets]


@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _own_ticket(db, ticket_id, current_user)
    return ticket_service.ticket_payload(db, ticket)


@router.post("/{ticket_id}/comments")
def add_comment(
    ticket_id: int,
    data: TicketComment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _own_ticket(db, ticket_id, current_user)
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    try:
        ticket_service.add_user_message(db, ticket, current_user, data.content.strip())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ticket_service.ticket_payload(db, ticket)


@router.post("/{ticket_id}/close")
def close_ticket(
    ticket_id: int,
    data: TicketUserClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = _own_ticket(db, ticket_id, current_user)
    try:
        ticket_service.user_close(db, ticket, current_user, data.note)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ticket_service.ticket_payload(db, ticket)


# ==================== 管理端 ====================


@admin_router.get("")
def admin_list_tickets(
    status: str | None = Query(None),
    assignee_id: int | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    tickets = ticket_service.list_all_tickets(db, status=status, assignee_id=assignee_id, keyword=q)
    return [
        ticket_service.ticket_payload(db, ticket, include_internal=False, mask=True)
        for ticket in tickets
    ]


@admin_router.get("/assignees")
def list_assignees(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .filter(User.is_active.is_(True))
        .filter((User.is_admin.is_(True)) | (User.role.in_(["agent", "system_admin"])))
        .order_by(User.username)
        .all()
    )
    return [{"id": user.id, "username": user.username, "role": user.role} for user in users]


@admin_router.get("/{ticket_id}")
def admin_get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ticket_service.ticket_payload(db, ticket, include_internal=True, mask=True)


@admin_router.put("/{ticket_id}")
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_support_staff),
):
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if data.assignee_id is not None:
        assignee = db.query(User).filter(User.id == data.assignee_id).first()
        if not assignee:
            raise HTTPException(status_code=400, detail="客服账号不存在")
    try:
        ticket_service.update_ticket(
            db,
            ticket,
            current_user,
            status=data.status,
            assignee_id=data.assignee_id,
            note=data.note,
            resolution=data.resolution,
            internal=data.internal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ticket_service.ticket_payload(db, ticket, include_internal=True, mask=True)
