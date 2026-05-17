"""
对话记录数据模型（Conversation ORM Model）

定义 Conversation（对话记录）表结构。
每次用户向 AI 提问并获得回答，都会在该表中生成一条记录。
用于用户查看历史对话、管理后台统计对话次数等场景。

后续可扩展为多轮对话（通过添加 parent_id 字段实现对话树结构）。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Conversation(Base):
    """
    对话记录表（conversations）的 ORM 模型

    存储用户与 AI 的每一次对话，包括用户的问题和 AI 的回答。
    """

    # ==================== 表名定义 ====================
    # 对应数据库中的 conversations 表，存储所有对话记录
    __tablename__ = "conversations"

    # ==================== 字段定义 ====================

    # 主键，自增整数
    # 每条对话记录都有唯一的 id，用于标识和查询
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键：关联到 users 表的 id 字段
    # 标识该条对话是由哪个用户发起的（提问者）
    # nullable=False 表示每条对话记录必须关联一个用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 外键：关联到 knowledge_bases 表的 id 字段
    # 标识该条对话使用了哪个知识库进行回答
    # nullable=True 表示对话可以不关联知识库（如通用问答场景）
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True)

    # 外键：关联到 sessions 表的 id 字段
    # nullable=True 兼容旧数据（旧对话没有 session_id）
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    # 用户的问题，使用 Text 类型支持较长文本
    # 用户提问可能包含大段文字或代码片段，因此使用 Text 而非 String
    question = Column(Text, nullable=False)

    # AI 的回答，使用 Text 类型支持较长文本
    # AI 回复通常较长，可能包含格式化内容、代码等
    answer = Column(Text, nullable=False)

    # 对话创建时间，数据库服务端自动生成默认值
    # 使用 server_default=func.now() 确保即使绕过 ORM 也能正确填充时间
    created_at = Column(DateTime, server_default=func.now())
