"""SQLAlchemy 数据库引擎、会话工厂和声明式基类。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


def get_db():
    """FastAPI 依赖注入：为每次请求提供数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
