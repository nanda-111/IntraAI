"""故障诊断会话、对话轮次与步骤 ORM 模型。"""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class DiagnosisSession(Base):
    """诊断会话（diagnosis_sessions），保存状态机与槽位快照。"""

    __tablename__ = "diagnosis_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnosis_uid = Column(String(60), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_id = Column(String(80), ForeignKey("product_models.model_id"), nullable=True, index=True)
    brand_code = Column(String(30), nullable=True)
    region = Column(String(20), default="CN")
    status = Column(String(30), default="MODEL_PENDING", nullable=False, index=True)
    fault_category = Column(String(40), nullable=True)
    brand_error_code = Column(String(60), nullable=True)
    symptom = Column(Text, nullable=True)
    slot_snapshot = Column(JSON, default=dict)
    evidence = Column(JSON, default=list)
    current_step_no = Column(Integer, default=0)
    escalation_required = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolution_note = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)


class DiagnosisTurn(Base):
    """诊断对话轮次（diagnosis_turns）。"""

    __tablename__ = "diagnosis_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnosis_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    state = Column(String(30), nullable=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())


class DiagnosisStep(Base):
    """诊断步骤（diagnosis_steps），每条步骤必须关联已审核知识。"""

    __tablename__ = "diagnosis_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnosis_sessions.id"), nullable=False, index=True)
    step_no = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    risk_level = Column(String(4), default="L1", nullable=False)
    expected_result = Column(Text, nullable=True)
    source_doc_id = Column(String(80), nullable=True)
    source_title = Column(String(220), nullable=True)
    source_url = Column(String(500), nullable=True)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending / ready / done / failed / skipped
    user_result = Column(Text, nullable=True)
    user_note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
