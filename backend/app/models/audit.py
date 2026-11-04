"""审计日志与用户反馈 ORM 模型。"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    """管理员和客服关键操作审计（audit_logs）。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(80), nullable=True)
    before_value = Column(Text, nullable=True)
    after_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class UserFeedback(Base):
    """用户反馈（user_feedback）。"""

    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    channel = Column(String(30), default="assistant")  # assistant / diagnosis / ticket
    reference_id = Column(Integer, nullable=True)
    rating = Column(Integer, default=5)
    resolved = Column(Boolean, default=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
