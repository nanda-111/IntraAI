"""智能客服 Schema。"""

from pydantic import BaseModel


class AssistantSessionCreate(BaseModel):
    model_id: str | None = None
    title: str | None = None


class AssistantMessageCreate(BaseModel):
    content: str
    fault_category: str | None = None
