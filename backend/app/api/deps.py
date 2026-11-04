"""FastAPI 依赖注入：当前用户获取和管理员权限检查。"""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT 令牌中解析出当前登录用户。无效令牌或用户已禁用时返回 401。"""
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的令牌")
    except JWTError as err:
        raise HTTPException(status_code=401, detail="无效的令牌") from err

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """检查当前用户是否为管理员。非管理员返回 403。"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ==================== 平台 RBAC ====================

ROLE_LABELS = {
    "user": "普通用户",
    "agent": "客服人员",
    "knowledge_admin": "知识库管理员",
    "system_admin": "系统管理员",
}


def effective_role(user: User) -> str:
    """兼容旧数据：is_admin=True 视为系统管理员。"""
    if user.role in {"agent", "knowledge_admin", "system_admin"}:
        return user.role
    return "system_admin" if user.is_admin else "user"


def get_system_admin(current_user: User = Depends(get_current_user)) -> User:
    if effective_role(current_user) != "system_admin":
        raise HTTPException(status_code=403, detail="需要系统管理员权限")
    return current_user


def get_knowledge_manager(current_user: User = Depends(get_current_user)) -> User:
    """品牌型号、知识、案例管理权限。"""
    if effective_role(current_user) not in {"knowledge_admin", "system_admin"}:
        raise HTTPException(status_code=403, detail="需要知识管理权限")
    return current_user


def get_support_staff(current_user: User = Depends(get_current_user)) -> User:
    """工单处理权限。"""
    if effective_role(current_user) not in {"agent", "system_admin"}:
        raise HTTPException(status_code=403, detail="需要客服或系统管理员权限")
    return current_user


def get_staff(current_user: User = Depends(get_current_user)) -> User:
    """任意运营端角色（可访问管理驾驶舱）。"""
    if effective_role(current_user) == "user":
        raise HTTPException(status_code=403, detail="需要运营端权限")
    return current_user
