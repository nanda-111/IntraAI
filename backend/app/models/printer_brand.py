"""品牌、型号、能力映射与用户设备偏好 ORM 模型。"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class PrinterBrand(Base):
    """品牌目录（printer_brands）。"""

    __tablename__ = "printer_brands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_code = Column(String(30), unique=True, nullable=False, index=True)
    name = Column(String(80), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active / inactive
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ProductModel(Base):
    """具体型号目录（product_models）。"""

    __tablename__ = "product_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(80), unique=True, nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("printer_brands.id"), nullable=False, index=True)
    series = Column(String(120), nullable=False)
    model_code = Column(String(80), nullable=True)
    name = Column(String(160), nullable=False)
    aliases = Column(JSON, default=list)
    region = Column(String(20), default="CN", nullable=False)
    technology = Column(String(40), default="inkjet", nullable=False)
    supported_features = Column(JSON, default=list)
    support_status = Column(String(20), default="planned", nullable=False, index=True)
    # planned / building / pilot / active / suspended
    official_source_count = Column(Integer, default=0)
    knowledge_coverage = Column(Integer, default=0)  # 已审核知识条数
    release_note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ModelCapability(Base):
    """型号能力与故障范围映射（model_capabilities）。"""

    __tablename__ = "model_capabilities"
    __table_args__ = (
        UniqueConstraint("model_id", "fault_category", name="uq_model_fault_category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(80), ForeignKey("product_models.model_id"), nullable=False, index=True)
    fault_category = Column(String(40), nullable=False)
    code_system = Column(String(60), nullable=True)
    supported_features = Column(JSON, default=list)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True)
    verified_status = Column(String(20), default="pending", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserDevice(Base):
    """用户设备列表与当前设备（user_devices）。"""

    __tablename__ = "user_devices"
    __table_args__ = (UniqueConstraint("user_id", "model_id", name="uq_user_device"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_id = Column(String(80), ForeignKey("product_models.model_id"), nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
