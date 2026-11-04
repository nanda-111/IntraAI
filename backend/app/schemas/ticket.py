"""工单 Schema。"""

from pydantic import BaseModel


class TicketCreate(BaseModel):
    title: str | None = None
    summary: str | None = None
    model_id: str | None = None
    brand_code: str | None = None
    contact: str | None = None
    contact_type: str = "phone"
    fault_category: str | None = None
    brand_error_code: str | None = None
    diagnosis_id: int | None = None
    priority: str = "normal"


class TicketUpdate(BaseModel):
    status: str | None = None
    assignee_id: int | None = None
    note: str | None = None
    resolution: str | None = None
    internal: bool = True


class TicketComment(BaseModel):
    content: str


class TicketUserClose(BaseModel):
    note: str | None = None
