"""文档 ORM 模型。"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """文档表（documents），存储上传到知识库的文件元数据。"""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, default=0)
    file_mtime = Column(Float, default=0, comment="文件修改时间戳，用于同步检测变更")
    chunk_count = Column(Integer, default=0)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
