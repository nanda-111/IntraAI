"""知识库 CRUD API 路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.knowledge_base import KBCreate, KBOut, KBUpdate

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库"])


@router.post("/", response_model=KBOut)
def create_kb(
    data: KBCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建知识库

    流程：
    1. FastAPI 自动验证请求体是否符合 KBCreate 的字段定义。
    2. 从 current_user 中获取 owner_id（当前登录用户的 ID），
       而非从前端传入——这是安全设计，防止用户伪造创建者。
    3. 将知识库对象添加到数据库会话并提交。
    4. db.refresh(kb) 的作用：
       刷新对象以获取数据库生成的字段值（如自增的 id 和 server_default 的 created_at）。
       如果不调用 refresh，kb.id 可能为 None，kb.created_at 也不会有值，
       因为这些值是在 INSERT 语句执行时由数据库生成的，Python 端的 ORM 对象并不知道。
    """
    kb = KnowledgeBase(name=data.name, description=data.description, owner_id=current_user.id)
    db.add(kb)
    db.commit()
    db.refresh(kb)  # 刷新以获取数据库自动生成的 id 和 created_at
    return kb


@router.get("/", response_model=list[KBOut])
def list_kbs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库列表

    权限逻辑：
    - 管理员：返回所有知识库，用于系统管理和全局视图。
    - 普通用户：只返回 owner_id 等于自己 ID 的知识库，实现数据隔离。
    """
    if current_user.is_admin:
        return db.query(KnowledgeBase).all()
    return db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == current_user.id).all()


@router.get("/{kb_id}", response_model=KBOut)
def get_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个知识库详情

    权限检查：
    1. 先查询数据库，如果不存在返回 404。
    2. 再检查当前用户是否有权查看（管理员或所有者），无权则返回 403。
    """
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")
    return kb


@router.put("/{kb_id}", response_model=KBOut)
def update_kb(
    kb_id: int,
    data: KBUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新知识库信息

    部分更新逻辑：
    - KBUpdate 中所有字段都是可选的。
    - 通过 "is not None" 判断用户是否传入了该字段（区别于传入 null）。
    - 只更新用户明确传入的字段，未传入的字段保持数据库中的原值不变。
    """
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改")
    if data.name is not None:
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description
    db.commit()
    db.refresh(kb)  # 刷新以获取 updated_at 等数据库自动更新的字段
    return kb


@router.delete("/{kb_id}")
def delete_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识库

    删除操作不返回 KBOut，因为资源已被删除，
    只返回一个简单的确认消息（HTTP 200 + JSON）。
    """
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")
    db.delete(kb)
    db.commit()
    return {"message": "已删除"}
