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
