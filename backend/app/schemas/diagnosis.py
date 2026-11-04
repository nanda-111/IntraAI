"""故障诊断 Schema。"""

from pydantic import BaseModel


class DiagnosisCreate(BaseModel):
    model_id: str | None = None
    brand_code: str | None = None
    region: str = "CN"
    symptom: str | None = None
    fault_category: str | None = None


class DiagnosisMessage(BaseModel):
    content: str


class StepResultSubmit(BaseModel):
    result: str  # done / failed / skipped
    note: str | None = None


class ConfirmModel(BaseModel):
    model_id: str


class CloseSession(BaseModel):
    resolved: bool = False
    note: str | None = None
