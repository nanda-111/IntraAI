"""用量日志 ORM 模型。"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class UsageLog(Base):
    """用量日志表（usage_logs），记录用户操作用于统计分析。"""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
