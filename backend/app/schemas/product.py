"""品牌、型号、能力与用户设备相关 Schema。"""

from pydantic import BaseModel, Field


class BrandCreate(BaseModel):
    brand_code: str
    name: str
    status: str = "active"
    description: str | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    description: str | None = None


class ModelCreate(BaseModel):
    model_id: str
    brand_code: str
    series: str
    model_code: str | None = None
    name: str
    aliases: list[str] = Field(default_factory=list)
    region: str = "CN"
    technology: str = "inkjet"
    supported_features: list[str] = Field(default_factory=list)
    support_status: str = "planned"
    release_note: str | None = None


class ModelUpdate(BaseModel):
    series: str | None = None
    model_code: str | None = None
    name: str | None = None
    aliases: list[str] | None = None
    region: str | None = None
    technology: str | None = None
    supported_features: list[str] | None = None
    support_status: str | None = None
    release_note: str | None = None


class CapabilityCreate(BaseModel):
    fault_category: str
    code_system: str | None = None
    supported_features: list[str] = Field(default_factory=list)
    source_id: int | None = None
    verified_status: str = "pending"
    notes: str | None = None


class CapabilityUpdate(BaseModel):
    code_system: str | None = None
    supported_features: list[str] | None = None
    source_id: int | None = None
    verified_status: str | None = None
    notes: str | None = None


class DeviceAdd(BaseModel):
    model_id: str
    set_current: bool = True
