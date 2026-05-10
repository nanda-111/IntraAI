"""
用户相关的 Pydantic Schema 定义

【Schema vs Model 的区别】
- SQLAlchemy Model（models/user.py）：定义数据库表结构，负责数据持久化（存取数据库）
- Pydantic Schema（本文件）：定义 API 请求/响应的数据格式，负责数据验证和序列化

为什么需要两套模型？
  1. 关注点分离：数据库层和 API 层的需求不同
  2. 安全控制：API 响应可以隐藏敏感字段（如密码哈希）
  3. 灵活性：请求和响应的数据结构往往不同

【Pydantic BaseModel 的作用】
- 自动类型校验：当 API 收到请求数据时，Pydantic 会自动验证每个字段的类型
  例如：如果 email 字段收到的不是字符串，会自动抛出验证错误
- JSON 序列化/反序列化：自动将 Python 对象转换为 JSON（响应时），
  或将 JSON 转换为 Python 对象（请求时）
"""

from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    用户注册请求的数据模型

    当用户调用注册接口时，请求体必须包含以下三个字段。
    Pydantic 会自动校验这些字段是否存在且类型正确。
    """
    username: str  # 用户名
    email: str  # 邮箱地址
    password: str  # 明文密码（在路由层会被哈希后存入数据库）


class UserLogin(BaseModel):
    """
    用户登录请求的数据模型

    登录时只需要用户名和密码，不需要邮箱。
    """
    username: str  # 用户名
    password: str  # 明文密码


class UserOut(BaseModel):
    """
    用户信息响应的数据模型

    【为什么不包含 hashed_password？】
    出于安全考虑，API 响应中绝不应该暴露密码哈希值。
    即使是哈希后的密码，也不应该通过 API 返回给客户端，
    以防止信息泄露和潜在的安全风险。

    【from_attributes = True 的作用】
    默认情况下，Pydantic 只能从字典（dict）中读取数据来创建模型实例。
    但 SQLAlchemy ORM 查询返回的是 ORM 对象（具有属性而非字典键）。
    设置 from_attributes = True 后，Pydantic 可以直接从 ORM 对象的
    属性中读取数据，实现 ORM 对象到 Pydantic 模型的自动转换。

    用法示例：
        user_db = session.query(User).first()  # SQLAlchemy ORM 对象
        user_schema = UserOut.model_validate(user_db)  # 自动转换为 Pydantic 模型
    """
    id: int  # 用户 ID（数据库自增主键）
    username: str  # 用户名
    email: str  # 邮箱地址
    is_admin: bool  # 是否为管理员
    is_active: bool  # 账户是否激活
    created_at: datetime  # 账户创建时间

    class Config:
        # 允许从 ORM 对象（而非字典）读取数据
        # 这是连接 SQLAlchemy Model 和 Pydantic Schema 的桥梁
        from_attributes = True


class Token(BaseModel):
    """
    JWT 令牌响应的数据模型

    登录成功后，API 返回此模型，包含访问令牌和用户信息。

    【token_type 默认值 "bearer" 的含义】
    "bearer" 是 HTTP 认证方案的标准类型，表示：
    "持有此令牌的人即为授权用户"。
    客户端在后续请求中应使用以下格式传递令牌：
        Authorization: Bearer <access_token>
    这是 OAuth 2.0 和 JWT 认证的行业标准做法。
    """
    access_token: str  # JWT 访问令牌
    token_type: str = "bearer"  # 令牌类型，默认为 "bearer"
    user: UserOut  # 登录用户的完整信息
