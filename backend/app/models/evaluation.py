"""评测数据集、评测任务与结果 ORM 模型。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class EvalDataset(Base):
    """评测数据集（eval_datasets），按品牌/型号分层。"""

    __tablename__ = "eval_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(160), nullable=False)
    brand_code = Column(String(30), nullable=True)
    model_id = Column(String(80), nullable=True)
    category = Column(String(40), nullable=True)  # retrieval / diagnosis / safety / ticket
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EvalItem(Base):
    """评测问题（eval_items）。"""

    __tablename__ = "eval_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("eval_datasets.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    expected_doc_ids = Column(JSON, default=list)
    expected_fault_category = Column(String(40), nullable=True)
    expected_escalation = Column(String(10), default="false")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class EvalRun(Base):
    """评测任务（eval_runs）。"""

    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("eval_datasets.id"), nullable=False, index=True)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending / running / finished / failed
    metrics = Column(JSON, default=dict)
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class EvalResult(Base):
    """单条评测结果（eval_results）。"""

    __tablename__ = "eval_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("eval_runs.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("eval_items.id"), nullable=False)
    question = Column(Text, nullable=False)
    retrieved_doc_ids = Column(JSON, default=list)
    recall5 = Column(Integer, default=0)  # 0 / 1
    reciprocal_rank = Column(Integer, default=0)  # 0 / 1
    fault_category = Column(String(40), nullable=True)
    fault_match = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    error = Column(Text, nullable=True)
