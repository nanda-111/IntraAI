"""会话相关 Pydantic 模型"""

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """创建会话的请求体（无字段，直接创建空会话）"""


class SessionOut(BaseModel):
    """会话的响应体"""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationItem(BaseModel):
    """单条对话记录（用于会话详情中的对话列表）"""

    id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    """会话详情（含对话记录列表）"""

    id: int
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    conversations: list[ConversationItem] = []

    class Config:
        from_attributes = True
