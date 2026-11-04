"""评测 Schema。"""

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str
    brand_code: str | None = None
    model_id: str | None = None
    category: str | None = "retrieval"
    description: str | None = None


class DatasetUpdate(BaseModel):
    name: str | None = None
    brand_code: str | None = None
    model_id: str | None = None
    category: str | None = None
    description: str | None = None


class EvalItemCreate(BaseModel):
    question: str
    expected_doc_ids: list[str] = Field(default_factory=list)
    expected_fault_category: str | None = None
    expected_escalation: bool = False
    notes: str | None = None


class FeedbackCreate(BaseModel):
    channel: str = "assistant"
    reference_id: int | None = None
    rating: int = 5
    resolved: bool = False
    comment: str | None = None
