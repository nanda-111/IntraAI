"""知识库 CRUD API 路由。"""

import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.schemas.knowledge_base import KBCreate, KBOut, KBUpdate
from app.services.vector_store import delete_collection

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库"])


@router.post("/", response_model=KBOut)
def create_kb(
    data: KBCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
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
    db.refresh(kb)
    # 创建知识库对应的上传目录
    os.makedirs(os.path.join(settings.UPLOAD_DIR, str(kb.id)), exist_ok=True)
    return kb


@router.post("/cleanup")
def cleanup_orphan_kbs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """清理数据库中已不存在对应文件夹的知识库（仅管理员）"""

    kbs = db.query(KnowledgeBase).all()
    removed = []
    for kb in kbs:
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb.id))
        if not os.path.isdir(upload_dir):
            # 清理关联数据
            delete_collection(kb.id)
            db.query(Conversation).filter(Conversation.kb_id == kb.id).delete()
            db.query(Document).filter(Document.kb_id == kb.id).delete()
            db.delete(kb)
            removed.append(kb.id)
    db.commit()
    return {"removed": removed, "count": len(removed)}


@router.get("/", response_model=list[KBOut])
def list_kbs(
    q: str | None = Query(None, description="按名称搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库列表（所有用户可查看，支持按名称搜索）"""
    query = db.query(KnowledgeBase)
    if q:
        # 使用 func.lower + like 替代 ilike，兼容 SQLite 和 MySQL
        query = query.filter(sql_func.lower(KnowledgeBase.name).like(f"%{q.lower()}%"))
    return query.all()


@router.get("/{kb_id}", response_model=KBOut)
def get_kb(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个知识库详情（所有用户可查看）"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb


@router.put("/{kb_id}", response_model=KBOut)
def update_kb(
    kb_id: int,
    data: KBUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """更新知识库信息（仅管理员）"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
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
    current_user: User = Depends(get_admin_user),
):
    """删除知识库（仅管理员，级联清理）"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 1. 删除上传的物理文件
    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    for doc in docs:
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    # 如果知识库对应的上传目录为空，删除目录
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb_id))
    if os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    # 2. 删除 ChromaDB 向量集合
    delete_collection(kb_id)

    # 3. 删除数据库关联记录
    db.query(Conversation).filter(Conversation.kb_id == kb_id).delete()
    db.query(Document).filter(Document.kb_id == kb_id).delete()

    # 4. 删除知识库本身
    db.delete(kb)
    db.commit()
    return {"message": "已删除"}
