"""售后工单业务：创建、用户跟踪、客服处理与状态流转。"""

from __future__ import annotations

import random
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisSession, DiagnosisStep
from app.models.service_ticket import ServiceTicket, TicketEvent
from app.models.user import User
from app.services.audit_service import log_action

TICKET_STATUSES = {
    "pending": "待受理",
    "assigned": "已分配",
    "processing": "处理中",
    "waiting_user": "待用户确认",
    "resolved": "已解决",
    "closed": "已关闭",
    "escalated": "已转专业维修",
}
ALLOWED_TRANSITIONS = {
    "pending": {"assigned", "processing", "closed", "escalated"},
    "assigned": {"processing", "waiting_user", "closed", "escalated"},
    "processing": {"waiting_user", "resolved", "closed", "escalated"},
    "waiting_user": {"processing", "resolved", "closed"},
    "resolved": {"closed", "processing"},
    "escalated": {"processing", "closed"},
    "closed": set(),
}


def generate_ticket_no() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"T{stamp}{random.randint(1000, 9999)}{uuid.uuid4().hex[:2].upper()}"


def mask_contact(contact: str | None) -> str | None:
    if not contact:
        return None
    if "@" in contact:
        name, domain = contact.split("@", 1)
        return f"{name[:2]}***@{domain}"
    if len(contact) <= 4:
        return "***"
    return f"{contact[:3]}***{contact[-2:]}"


def create_ticket(
    db: Session,
    user: User,
    *,
    title: str,
    summary: str | None = None,
    model_id: str | None = None,
    brand_code: str | None = None,
    contact: str | None = None,
    contact_type: str = "phone",
    fault_category: str | None = None,
    brand_error_code: str | None = None,
    diagnosis: DiagnosisSession | None = None,
    priority: str = "normal",
) -> ServiceTicket:
    if diagnosis:
        model_id = model_id or diagnosis.model_id
        brand_code = brand_code or diagnosis.brand_code
        fault_category = fault_category or diagnosis.fault_category
        brand_error_code = brand_error_code or diagnosis.brand_error_code
        if not summary:
            summary = diagnosis.summary or diagnosis.symptom
    ticket = ServiceTicket(
        ticket_no=generate_ticket_no(),
        user_id=user.id,
        diagnosis_id=diagnosis.id if diagnosis else None,
        brand_code=brand_code,
        model_id=model_id,
        title=title[:220],
        summary=summary,
        contact=contact,
        contact_type=contact_type,
        fault_category=fault_category,
        brand_error_code=brand_error_code,
        executed_steps=_diagnosis_steps(db, diagnosis) if diagnosis else [],
        evidence=(diagnosis.evidence if diagnosis else []) or [],
        priority=priority if priority in {"low", "normal", "high"} else "normal",
        status="pending",
    )
    db.add(ticket)
    db.flush()

    event = TicketEvent(
        ticket_id=ticket.id,
        actor_id=user.id,
        event_type="created",
        content="用户确认并创建工单",
        before_status=None,
        after_status="pending",
    )
    db.add(event)
    if diagnosis:
        diagnosis.status = "TICKET_OPEN"
        diagnosis.escalation_required = False
        db.add(diagnosis)
    db.commit()
    db.refresh(ticket)
    return ticket


def _diagnosis_steps(db: Session, diagnosis: DiagnosisSession | None) -> list[dict]:
    if not diagnosis:
        return []
    steps = (
        db.query(DiagnosisStep)
        .filter(DiagnosisStep.diagnosis_id == diagnosis.id)
        .order_by(DiagnosisStep.step_no)
        .all()
    )
    return [
        {
            "step_no": step.step_no,
            "instruction": step.instruction,
            "status": step.status,
            "source_doc_id": step.source_doc_id,
        }
        for step in steps
    ]


def list_tickets(db: Session, user: User, status: str | None = None) -> list[ServiceTicket]:
    query = db.query(ServiceTicket).filter(ServiceTicket.user_id == user.id)
    if status:
        query = query.filter(ServiceTicket.status == status)
    return query.order_by(ServiceTicket.created_at.desc()).all()


def list_all_tickets(
    db: Session,
    status: str | None = None,
    assignee_id: int | None = None,
    keyword: str | None = None,
) -> list[ServiceTicket]:
    query = db.query(ServiceTicket)
    if status:
        query = query.filter(ServiceTicket.status == status)
    if assignee_id:
        query = query.filter(ServiceTicket.assignee_id == assignee_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            ServiceTicket.title.like(like)
            | ServiceTicket.ticket_no.like(like)
            | ServiceTicket.model_id.like(like)
        )
    return query.order_by(ServiceTicket.created_at.desc()).all()


def update_ticket(
    db: Session,
    ticket: ServiceTicket,
    operator: User,
    *,
    status: str | None = None,
    assignee_id: int | None = None,
    note: str | None = None,
    resolution: str | None = None,
    internal: bool = True,
) -> ServiceTicket:
    before = ticket.status
    if status and status != ticket.status:
        if status not in TICKET_STATUSES:
            raise ValueError("无效的工单状态")
        if status not in ALLOWED_TRANSITIONS.get(ticket.status, set()):
            raise ValueError(
                f"不允许从“{TICKET_STATUSES.get(ticket.status, ticket.status)}”"
                f"变更为“{TICKET_STATUSES.get(status, status)}”"
            )
        ticket.status = status
        if status in {"resolved", "closed"}:
            ticket.closed_at = datetime.now()
    if assignee_id is not None:
        ticket.assignee_id = assignee_id
        if ticket.status == "pending":
            ticket.status = "assigned"
    if resolution is not None:
        ticket.resolution = resolution
    ticket.updated_at = datetime.now()
    db.add(ticket)

    if note or status != before or assignee_id is not None:
        event = TicketEvent(
            ticket_id=ticket.id,
            actor_id=operator.id,
            event_type="status_changed" if status != before else "comment",
            content=note or ("状态更新" if status != before else "客服补充记录"),
            before_status=before,
            after_status=ticket.status,
            is_internal="true" if internal else "false",
        )
        db.add(event)
    log_action(
        db,
        operator,
        "ticket.update",
        "service_ticket",
        ticket.ticket_no,
        before={"status": before, "assignee_id": ticket.assignee_id},
        after={"status": ticket.status, "assignee_id": ticket.assignee_id},
        reason=note,
        commit=False,
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def add_user_message(db: Session, ticket: ServiceTicket, user: User, content: str) -> TicketEvent:
    if ticket.user_id != user.id:
        raise PermissionError("无权操作该工单")
    event = TicketEvent(
        ticket_id=ticket.id,
        actor_id=user.id,
        event_type="comment",
        content=content,
        before_status=ticket.status,
        after_status=ticket.status,
        is_internal="false",
    )
    db.add(event)
    if ticket.status == "waiting_user":
        ticket.status = "processing"
    ticket.updated_at = datetime.now()
    db.add(ticket)
    db.commit()
    db.refresh(event)
    return event


def user_close(
    db: Session, ticket: ServiceTicket, user: User, note: str | None = None
) -> ServiceTicket:
    if ticket.user_id != user.id:
        raise PermissionError("无权操作该工单")
    if ticket.status in {"closed"}:
        return ticket
    before = ticket.status
    ticket.status = "closed"
    ticket.close_reason = note or "用户确认已解决"
    ticket.closed_at = datetime.now()
    db.add(ticket)
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            actor_id=user.id,
            event_type="closed",
            content=ticket.close_reason,
            before_status=before,
            after_status="closed",
            is_internal="false",
        )
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def ticket_payload(
    db: Session, ticket: ServiceTicket, include_internal: bool = False, mask: bool = False
) -> dict:
    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket.id)
        .order_by(TicketEvent.created_at, TicketEvent.id)
        .all()
    )
    assignee = (
        db.query(User).filter(User.id == ticket.assignee_id).first() if ticket.assignee_id else None
    )
    user = db.query(User).filter(User.id == ticket.user_id).first()
    return {
        "id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "title": ticket.title,
        "summary": ticket.summary,
        "status": ticket.status,
        "status_label": TICKET_STATUSES.get(ticket.status, ticket.status),
        "priority": ticket.priority,
        "brand_code": ticket.brand_code,
        "model_id": ticket.model_id,
        "fault_category": ticket.fault_category,
        "brand_error_code": ticket.brand_error_code,
        "contact": mask_contact(ticket.contact) if mask else ticket.contact,
        "contact_type": ticket.contact_type,
        "diagnosis_id": ticket.diagnosis_id,
        "executed_steps": ticket.executed_steps or [],
        "evidence": ticket.evidence or [],
        "assignee": {"id": assignee.id, "username": assignee.username} if assignee else None,
        "user": {"id": user.id, "username": user.username} if user else None,
        "resolution": ticket.resolution,
        "close_reason": ticket.close_reason,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "content": event.content,
                "before_status": event.before_status,
                "after_status": event.after_status,
                "internal": event.is_internal == "true",
                "actor_id": event.actor_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
            if include_internal or event.is_internal != "true"
        ],
    }
