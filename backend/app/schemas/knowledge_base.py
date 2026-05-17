"""
知识库 Pydantic Schema（数据验证与序列化模型）

本模块定义知识库 CRUD 接口所需的请求/响应数据结构。
Pydantic 模型的作用：
  1. 请求体验证：FastAPI 自动将前端传来的 JSON 解析为对应的 Pydantic 对象，
     如果字段类型不匹配或缺少必填字段，会自动返回 422 错误。
  2. 响应体序列化：通过 response_model 指定，FastAPI 会将 ORM 对象
     自动转换为 JSON 输出，过滤掉不需要暴露的字段。
"""

from datetime import datetime

from pydantic import BaseModel


class KBCreate(BaseModel):
    """创建知识库的请求体

    设计思路：
    - name 必填：知识库必须有名称，用于在列表中展示和区分。
    - description 可选：有些用户可能只想快速创建，暂不填写描述。
    - owner_id 不可由前端指定：由后端从当前登录用户的 JWT 令牌中自动提取，
      防止用户伪造创建者身份（安全考虑）。
    """

    name: str
    description: str | None = None


class KBUpdate(BaseModel):
    """更新知识库的请求体

    设计思路：
    - 所有字段均为可选（使用 | None = None）：支持部分更新（PATCH 语义）。
      用户只需传入想修改的字段，未传入的字段保持原值。
    - 在路由处理函数中通过 "if data.name is not None" 来判断用户是否传入了该字段。
    """

    name: str | None = None
    description: str | None = None


class KBOut(BaseModel):
    """知识库的响应体（用于 GET 和返回创建/更新后的结果）

    设计思路：
    - 包含 id、owner_id、created_at 等只读字段，由数据库自动生成。
    - 未包含 updated_at：对前端而言通常不需要展示更新时间，
      如果后续需要可以扩展。
    - from_attributes = True：告诉 Pydantic 可以从 ORM 对象的属性中读取数据，
      而不仅仅从字典中读取。这是 SQLAlchemy + Pydantic 集成的关键配置。
    """

    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
