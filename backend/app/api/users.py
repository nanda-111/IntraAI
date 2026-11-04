"""用户个人资料接口。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户的信息。"""
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新个人资料（邮箱需唯一）。"""
    if data.email and data.email != current_user.email:
        exists = db.query(User).filter(User.email == data.email, User.id != current_user.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="邮箱已被其他账号使用")
        current_user.email = data.email
    if data.display_name is not None:
        current_user.display_name = data.display_name
    if data.phone is not None:
        current_user.phone = data.phone
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改密码。"""
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    current_user.hashed_password = hash_password(data.new_password)
    db.add(current_user)
    db.commit()
    return {"message": "密码已更新"}
