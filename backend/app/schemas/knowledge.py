"""知识来源、知识条目与审核相关 Schema。"""

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    source_key: str | None = None
    title: str
    url: str | None = None
    source_type: str = "official"
    authority_level: str = "A"
    brand_code: str | None = None
    model_scope: str | None = None
    region_scope: str = "CN"
    version: str = "1.0"
    license_note: str | None = None
    verified_status: str = "verified"


class SourceUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    source_type: str | None = None
    authority_level: str | None = None
    brand_code: str | None = None
    model_scope: str | None = None
    region_scope: str | None = None
    version: str | None = None
    license_note: str | None = None
    verified_status: str | None = None


class KnowledgeCreate(BaseModel):
    title: str
    source_id: int | None = None
    brand_code: str
    series: str | None = None
    model_scope: str
    region_scope: str = "CN"
    code_system: str | None = None
    fault_category: str
    fault_code: str | None = None
    symptom: str | None = None
    possible_causes: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[dict] = Field(default_factory=list)
    expected_result: str | None = None
    verification_method: str | None = None
    safety_warnings: list[str] = Field(default_factory=list)
    risk_level: str = "L1"
    source_type: str = "manual"
    authority_level: str = "C"
    review_status: str = "draft"


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    source_id: int | None = None
    brand_code: str | None = None
    series: str | None = None
    model_scope: str | None = None
    region_scope: str | None = None
    code_system: str | None = None
    fault_category: str | None = None
    fault_code: str | None = None
    symptom: str | None = None
    possible_causes: list[str] | None = None
    preconditions: list[str] | None = None
    steps: list[dict] | None = None
    expected_result: str | None = None
    verification_method: str | None = None
    safety_warnings: list[str] | None = None
    risk_level: str | None = None
    source_type: str | None = None
    authority_level: str | None = None
    version: str | None = None


class ReviewRequest(BaseModel):
    action: str
    note: str | None = None
