"""
用户管理路由模块

提供获取当前登录用户信息的接口。
用户必须携带有效的 JWT 令牌才能访问此模块的接口。

【路由前缀】/api/users
【认证要求】所有接口均需 JWT 认证
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut

# 创建用户路由实例
# prefix: 所有路由的 URL 前缀，此处为 /api/users
# tags: 用于 Swagger 文档中的分组标签，方便在 /docs 页面中归类展示
router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息

    【接口说明】
      客户端在请求头中携带 JWT 令牌（Authorization: Bearer <token>），
      后端通过 get_current_user 依赖自动解析令牌并查询数据库，
      返回当前用户的完整信息（不含密码哈希）。

    【Depends(get_current_user) 的作用】
      - FastAPI 会在执行此函数之前，先调用 get_current_user
      - get_current_user 负责：提取令牌 → 解码 JWT → 查询用户 → 校验状态
      - 如果任何一步失败，会直接返回 401 错误，不会执行到此处
      - 解析成功的 User 对象会注入到 current_user 参数中

    Args:
        current_user: 由依赖注入自动提供的当前登录用户对象

    Returns:
        UserOut: 当前用户的公开信息（id、用户名、邮箱、管理员标志等）
    """
    return current_user
