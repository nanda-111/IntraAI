"""用户 ORM 模型。"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """用户表（users）。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(80), nullable=True)
    phone = Column(String(30), nullable=True)
    # RBAC 角色：user / agent（客服）/ knowledge_admin（知识管理员）/ system_admin（系统管理员）
    role = Column(String(30), default="user", nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
