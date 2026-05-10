"""
文档数据模型

定义 Document（文档）表结构。
文档是知识库的基本组成单元，记录用户上传的原始文件元数据。
后续会对文档进行切片（chunking）并生成向量嵌入（embedding），供 RAG 检索使用。
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """文档表 — 存储上传到知识库的文档元数据"""

    __tablename__ = "documents"

    # 主键，自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 原始文件名（用户上传时的文件名），String(255) 足以覆盖大多数文件名
    filename = Column(String(255), nullable=False)

    # 文件在服务器上的存储路径，String(500) 支持较长的目录路径
    filepath = Column(String(500), nullable=False)

    # 文件类型标识，限定为 pdf / docx / txt / md 等
    # 使用 String(20) 而非枚举，方便后续扩展新格式
    file_type = Column(String(20), nullable=False)

    # 文件大小（字节），Integer 足以表示 2GB 以内的文件
    file_size = Column(Integer, default=0)

    # 文档被切分的片段数量
    # chunk_count 的用途：
    #   当文档被送入向量化流程时，会被切分为若干文本片段（chunk）。
    #   每个片段独立生成向量嵌入并存入向量数据库。
    #   此字段记录切片总数，便于：
    #     1. 前端展示文档处理进度（如"已切分为 42 个片段"）
    #     2. 后端判断文档是否已完成向量化（chunk_count > 0 表示已处理）
    #     3. 统计知识库的总切片规模，用于容量规划
    chunk_count = Column(Integer, default=0)

    # 外键：关联到 knowledge_bases 表，表示此文档属于哪个知识库
    # 级联关系：删除知识库时，可通过数据库配置 CASCADE 策略一并删除其下所有文档
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=False)

    # 外键：关联到 users 表，记录上传此文档的用户
    # 用于审计追踪，明确文档归属
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 记录上传时间，数据库服务端自动生成
    created_at = Column(DateTime, server_default=func.now())
