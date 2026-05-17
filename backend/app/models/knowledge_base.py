"""
知识库数据模型

定义 KnowledgeBase（知识库）表结构。
每个用户可以创建多个知识库，每个知识库用于存储一批关联文档，
后续可对知识库内的文档进行切片、向量化，供检索增强生成（RAG）使用。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class KnowledgeBase(Base):
    """知识库表 — 存储用户创建的知识库信息"""

    __tablename__ = "knowledge_bases"

    # 主键，自增整数
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 知识库名称，String(100) 限定最大 100 字符
    # 使用 String 而非 Text，因为名称通常长度有限，String 可以加索引
    name = Column(String(100), nullable=False)

    # 知识库描述，使用 Text 类型支持较长文本
    # Text vs String 的区别：
    #   - String(n) 在数据库中存储为 VARCHAR(n)，有长度上限，可加唯一约束和索引
    #   - Text 存储为 TEXT/CLOB，无固定长度上限，适合大段描述文字
    description = Column(Text, nullable=True)

    # 外键：关联到 users 表的 id 字段
    # ForeignKey 的作用：
    #   1. 数据库层面建立表间关联，保证 owner_id 的值必须存在于 users.id 中
    #   2. 防止出现"孤儿数据"——删除用户时可配置级联删除其知识库
    #   3. SQLAlchemy 可通过 relationship 方便地做联表查询
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 记录创建时间，数据库服务端自动生成默认值
    created_at = Column(DateTime, server_default=func.now())

    # 记录更新时间，每次行更新时自动刷新
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
