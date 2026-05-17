"""
认证路由模块（Authentication Routes）

提供用户注册和用户登录两个 API 接口。

【认证 vs 授权的区别】
  - 认证（Authentication）：验证"你是谁"——通过用户名和密码确认用户身份。
  - 授权（Authorization）：验证"你能做什么"——检查用户是否有权限执行某个操作。
  本模块处理的是认证逻辑，授权逻辑在 deps.py 中实现（如 get_admin_user）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

# ==================== 路由器定义 ====================
# APIRouter 是 FastAPI 的路由器类，用于将相关的路由组织在一起。
# - prefix="/api/auth"：所有路由的 URL 前缀，如 /api/auth/register、/api/auth/login。
#   使用前缀可以统一管理 URL 结构，避免路由冲突。
# - tags=["认证"]：在 Swagger 文档中将这些路由归类到"认证"标签下，
#   方便开发者在文档中浏览和测试。
router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=UserOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册接口。

    处理流程：
      1. 检查用户名是否已被注册（数据库唯一约束兜底，但在应用层检查更友好）。
      2. 检查邮箱是否已被注册。
      3. 判断是否为系统中的第一个用户——
         【第一个用户自动成为管理员的设计意图】
         这是一种"自举"（Bootstrapping）策略：
         - 系统初始部署时没有任何用户，也没有管理员。
         - 如果不采用此策略，就需要手动修改数据库来创建第一个管理员，
           这在容器化部署或 CI/CD 环境中非常不便。
         - 因此，让第一个注册的用户自动成为管理员，是一种简单且安全的方案。
         - 之后注册的用户默认为普通用户，管理员可以后续手动提升权限。
         这种模式在很多开源项目中都有使用（如 WordPress、Redmine 等）。
      4. 对明文密码进行 bcrypt 哈希处理。
      5. 将用户信息存入数据库。
      6. 返回用户信息（不含密码哈希，由 UserOut schema 控制）。

    Args:
        data: 用户注册请求数据（用户名、邮箱、密码），由 Pydantic 自动验证
        db: 数据库会话，由 FastAPI 依赖注入自动提供

    Returns:
        新创建用户的详细信息（UserOut 格式）

    Raises:
        HTTPException 400: 用户名已存在或邮箱已注册
    """
    # 检查用户名是否已被注册
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    # 检查邮箱是否已被注册
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已注册")

    # 判断是否为系统中的第一个用户
    # 如果是，自动授予管理员权限（is_admin = True）
    is_first = db.query(User).count() == 0

    # 创建 User ORM 对象
    # 注意：password 在这里经过 hash_password() 哈希后才存入 hashed_password 字段
    # 绝不能将明文密码存入数据库
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_admin=is_first,
    )
    db.add(user)  # 将新用户添加到数据库会话
    db.commit()  # 提交事务，将数据持久化到数据库
    db.refresh(user)  # 刷新对象，获取数据库生成的字段（如 id、created_at）
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录接口。

    【为什么 login 返回 token 而不是用户信息？】
      这是 RESTful API 和 JWT 认证的标准做法：
      1. 关注点分离：登录接口的职责是"验证身份并发放凭证"，
         而不是"获取用户信息"。获取用户信息应该由专门的接口（如 /api/users/me）负责。
      2. 无状态认证：JWT 令牌是自包含的（self-contained），里面已经编码了用户名等信息。
         客户端拿到 token 后，可以在后续请求中直接使用它来证明身份，
         服务端不需要在服务器端维护会话状态。
      3. 安全性：减少单个接口返回的信息量，降低信息泄露的风险。
      4. 灵活性：客户端可以在需要时通过不同接口获取不同粒度的用户信息，
         而不是在登录时一次性获取所有信息。

      本接口仍然返回了基本的用户信息（通过 Token 中的 user 字段），
      这是为了方便前端在登录后立即展示用户信息，减少一次额外的 API 调用。

    处理流程：
      1. 根据用户名查询数据库中的用户记录。
      2. 使用 bcrypt 验证明文密码是否与数据库中的哈希值匹配。
      3. 检查用户账号是否处于激活状态（is_active = True）。
      4. 生成 JWT 访问令牌（包含用户名和过期时间）。
      5. 返回令牌和用户信息。

    Args:
        data: 用户登录请求数据（用户名、密码），由 Pydantic 自动验证
        db: 数据库会话，由 FastAPI 依赖注入自动提供

    Returns:
        JWT 令牌和用户信息（Token 格式，包含 access_token、token_type、user）

    Raises:
        HTTPException 401: 用户名或密码错误
        HTTPException 403: 账号已被禁用
    """
    # 根据用户名查询用户
    user = db.query(User).filter(User.username == data.username).first()
    # 验证密码：如果用户不存在或密码不匹配，返回相同的错误信息
    # （不区分"用户不存在"和"密码错误"，防止用户名枚举攻击）
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 检查账号是否被禁用
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    # 生成 JWT 访问令牌
    # payload 中包含 {"sub": username}，sub 是用户名的标识
    # 过期时间由 create_access_token 内部根据配置自动计算
    token = create_access_token({"sub": user.username})
    # 返回令牌和用户信息
    # token_type="bearer" 告诉客户端使用 Bearer 认证方案
    return Token(access_token=token, user=user)
