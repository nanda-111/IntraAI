"""
文档相关的 Pydantic 数据模型（Schema）

这些模型用于 API 请求/响应的数据验证和序列化。
Pydantic 会自动验证传入数据的类型和格式，确保数据完整性。
"""

from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    """
    文档响应模型 — 返回给前端的文档信息。

    当 FastAPI 路由的 response_model 设置为 DocumentOut 时，
    会自动将 SQLAlchemy 的 Document 模型实例转换为此 Pydantic 模型，
    并过滤掉不需要暴露给前端的字段（如 filepath、uploaded_by）。
    """
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    kb_id: int
    created_at: datetime

    class Config:
        """
        Pydantic v2 的配置类。

        from_attributes = True 允许 Pydantic 直接从 ORM 对象（如 SQLAlchemy 模型实例）
        的属性中读取数据，而不仅限于字典。
        这使得我们可以直接返回 SQLAlchemy 模型实例，Pydantic 会自动将其转换为 JSON 响应。
        """
        from_attributes = True
