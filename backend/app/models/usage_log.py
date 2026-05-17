"""
用量日志数据模型（UsageLog ORM Model）

定义 UsageLog（用量日志）表结构。
记录用户的每一次操作（对话、上传、搜索等），
用于管理后台的统计分析（调用次数、活跃用户数等），
后续可扩展为计费依据（记录 Token 消耗量）。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class UsageLog(Base):
    """
    用量日志表（usage_logs）的 ORM 模型

    记录用户的每一次操作，包括操作类型和 Token 消耗量。
    管理后台可通过该表统计系统使用情况。
    """

    # ==================== 表名定义 ====================
    # 对应数据库中的 usage_logs 表，存储所有操作日志
    __tablename__ = "usage_logs"

    # ==================== 字段定义 ====================

    # 主键，自增整数
    # 每条日志记录都有唯一的 id
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键：关联到 users 表的 id 字段
    # 标识该条日志是由哪个用户触发的操作
    # nullable=False 表示每条日志必须关联一个用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 操作类型，使用 String(50) 限定最大 50 字符
    # 常见操作类型包括：
    #   - chat：对话操作（用户向 AI 提问）
    #   - upload：上传操作（用户上传文档到知识库）
    #   - search：搜索操作（用户在知识库中检索信息）
    # 使用 String 而非枚举类型，便于后续扩展新的操作类型
    action = Column(String(50), nullable=False)

    # 消耗的 Token 数量
    # Token 是大语言模型的计费单位，一次对话可能消耗几十到几千个 Token
    # default=0：对于非对话类操作（如上传），Token 消耗为 0
    # Integer 类型足以覆盖大多数场景的 Token 消耗量
    tokens_used = Column(Integer, default=0)

    # 日志创建时间，数据库服务端自动生成默认值
    # 使用 server_default=func.now() 确保记录操作发生的时间
    created_at = Column(DateTime, server_default=func.now())
