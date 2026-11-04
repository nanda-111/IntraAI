"""智能客服会话、消息与检索日志 ORM 模型。"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class PrinterChatSession(Base):
    """智能客服会话（printer_chat_sessions）。"""

    __tablename__ = "printer_chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_id = Column(String(80), ForeignKey("product_models.model_id"), nullable=True)
    title = Column(String(220), default="新的咨询", nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PrinterChatMessage(Base):
    """智能客服消息（printer_chat_messages）。"""

    __tablename__ = "printer_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("printer_chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    intent = Column(String(40), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RetrievalLog(Base):
    """检索链路日志（retrieval_logs），用于定位跨型号过滤错误。"""

    __tablename__ = "retrieval_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    channel = Column(
        String(30), default="assistant"
    )  # assistant / diagnosis / knowledge / evaluation
    model_id = Column(String(80), nullable=True)
    query = Column(Text, nullable=False)
    filters = Column(JSON, default=dict)
    vector_candidates = Column(Integer, default=0)
    bm25_candidates = Column(Integer, default=0)
    rerank_count = Column(Integer, default=0)
    source_doc_ids = Column(JSON, default=list)
    evidence_passed = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
