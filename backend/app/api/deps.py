"""
依赖注入模块（Dependency Injection）

本模块提供 FastAPI 路由中常用的依赖函数，用于：
  1. 从 JWT 令牌中解析并获取当前登录用户
  2. 检查当前用户是否具有管理员权限

【FastAPI 依赖注入的原理（Depends）】
  FastAPI 的依赖注入系统是一种"控制反转"（IoC）机制：
  - 你不需要在路由函数中手动调用数据库连接、用户认证等逻辑，
    而是通过 Depends() 声明"我需要什么依赖"。
  - FastAPI 框架会在执行路由函数之前，自动解析依赖链并依次执行。
  - 依赖可以嵌套：一个依赖可以依赖另一个依赖（如 get_admin_user 依赖 get_current_user）。
  - 依赖的返回值会自动注入到路由函数的参数中。
  - 同一请求中，相同的依赖只会执行一次（结果被缓存），避免重复计算。

  例如：
    @router.get("/profile")
    def get_profile(user: User = Depends(get_current_user)):
        # FastAPI 会自动：
        # 1. 从请求头中提取 token（通过 oauth2_scheme）
        # 2. 调用 get_current_user 解析 token 并查询用户
        # 3. 将 User 对象注入到 user 参数
        # 4. 然后才执行函数体
        return user
"""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# ==================== OAuth2PasswordBearer 详解 ====================
#
# OAuth2PasswordBearer 是 FastAPI 提供的一个类，用于实现 OAuth2 密码模式的令牌提取。
#
# 【工作机制】
#   1. 当一个路由函数的参数中使用了 Depends(oauth2_scheme) 时，
#      FastAPI 会自动从 HTTP 请求头中查找 "Authorization" 字段。
#   2. 它期望的格式是 "Authorization: Bearer <token>"，
#      其中 "Bearer " 是固定的前缀，后面紧跟 JWT 令牌字符串。
#   3. OAuth2PasswordBearer 会自动去掉 "Bearer " 前缀，
#      将纯令牌字符串传递给依赖函数（如 get_current_user）。
#   4. 如果请求头中缺少 Authorization 字段或格式不正确，
#      FastAPI 会自动返回 401 Unauthorized 错误，无需手动处理。
#
# 【tokenUrl 参数的作用】
#   tokenUrl="/api/auth/login" 仅用于 Swagger 文档（/docs）：
#   - 它告诉 Swagger UI 登录接口的地址。
#   - 在 Swagger 文档页面点击"Authorize"按钮时，会弹出登录表单。
#   - 用户输入用户名密码后，Swagger 会向 tokenUrl 发送请求获取 token。
#   - 之后 Swagger 发送其他请求时，会自动在请求头中携带这个 token。
#   - 该参数不会影响实际的 API 逻辑，仅仅是文档辅助功能。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从 JWT 令牌中解析出当前登录用户。

    【JWT 认证流程：token → 解码 → 查用户】
      1. 客户端在请求头中携带 "Authorization: Bearer <token>"。
      2. oauth2_scheme 从请求头中提取出 token 字符串。
      3. decode_access_token() 使用服务端的 SECRET_KEY 验证签名并解码 payload。
         - 如果令牌被篡改（签名不匹配）或已过期，会抛出 JWTError。
      4. 从解码后的 payload 中取出 "sub" 字段（即用户名）。
      5. 用用户名查询数据库，获取完整的 User 对象。
      6. 检查用户是否存在且处于激活状态（is_active = True）。
      7. 返回 User 对象，供路由函数使用。

    任何一步失败都会抛出 401 未授权异常，阻止后续逻辑执行。

    Args:
        token: 由 oauth2_scheme 自动提取的 JWT 令牌字符串
        db: 由 get_db 自动注入的数据库会话

    Returns:
        当前登录用户的 User ORM 对象

    Raises:
        HTTPException 401: 令牌无效、用户不存在或用户已被禁用
    """
    try:
        # 解码 JWT 令牌，获取 payload（包含 sub、exp 等字段）
        payload = decode_access_token(token)
        # 从 payload 中提取用户名（"sub" 是 JWT 标准中的主题声明）
        username: str = payload.get("sub")
        if username is None:
            # payload 中缺少 sub 字段，说明令牌格式不正确
            raise HTTPException(status_code=401, detail="无效的令牌")
    except JWTError:
        # 令牌签名验证失败、令牌过期或其他 JWT 解析错误
        raise HTTPException(status_code=401, detail="无效的令牌")

    # 根据用户名查询数据库
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        # 用户不存在，或账号已被禁用（is_active = False）
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    检查当前用户是否为管理员。

    【依赖链的工作方式】
      此函数依赖 get_current_user，形成如下调用链：
        请求 → oauth2_scheme 提取 token
             → get_current_user 解码 token 并查询用户
             → get_admin_user 检查 is_admin 标志
             → 路由函数

      FastAPI 会自动按顺序解析整条依赖链。get_current_user 返回的 User 对象
      会被注入到 current_user 参数中，无需手动传递。

    Args:
        current_user: 由 get_current_user 自动注入的当前用户对象

    Returns:
        具有管理员权限的 User 对象

    Raises:
        HTTPException 403: 用户不是管理员（拒绝访问）
    """
    if not current_user.is_admin:
        # 用户已认证但权限不足，返回 403 Forbidden（区别于 401 Unauthorized）
        # 401 = 未认证（没有登录），403 = 已认证但无权限
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
