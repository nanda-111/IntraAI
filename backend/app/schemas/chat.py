"""对话相关的 Pydantic 模型（请求/响应 schema）"""

from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None
    mode: Literal["normal", "agent"] = "normal"
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    kb_id: int | None = None
