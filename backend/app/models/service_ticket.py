"""售后工单与流转记录 ORM 模型。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ServiceTicket(Base):
    """售后工单（service_tickets）。"""

    __tablename__ = "service_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_no = Column(String(40), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnosis_sessions.id"), nullable=True)
    brand_code = Column(String(30), nullable=True)
    model_id = Column(String(80), nullable=True, index=True)
    title = Column(String(220), nullable=False)
    summary = Column(Text, nullable=True)
    contact = Column(String(120), nullable=True)
    contact_type = Column(String(20), default="phone")
    fault_category = Column(String(40), nullable=True)
    brand_error_code = Column(String(60), nullable=True)
    executed_steps = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    priority = Column(String(10), default="normal", nullable=False)  # low / normal / high
    status = Column(String(30), default="pending", nullable=False, index=True)
    # pending / assigned / processing / waiting_user / resolved / closed / escalated
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution = Column(Text, nullable=True)
    close_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)


class TicketEvent(Base):
    """工单流转记录（ticket_events）。"""

    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("service_tickets.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(
        String(40), nullable=False
    )  # created / assigned / status_changed / comment / closed
    content = Column(Text, nullable=True)
    before_status = Column(String(30), nullable=True)
    after_status = Column(String(30), nullable=True)
    is_internal = Column(String(10), default="false")
    created_at = Column(DateTime, server_default=func.now())
