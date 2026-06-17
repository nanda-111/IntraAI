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
from app.services.document_processor import extract_text_with_pages, split_document
from app.services.embedding import get_embeddings
from app.services.vector_store import add_documents, delete_by_source, delete_collection

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


# ==================== 文件夹同步 ====================

ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}
BATCH_SIZE = 100


def _process_file(filepath: str, filename: str, ext: str, kb_id: int, user_id: int, db: Session):
    """处理单个文件：提取文本 → 切片 → 向量化 → 存入 ChromaDB + 数据库。"""
    pages = extract_text_with_pages(filepath, ext)
    if not pages:
        return 0

    all_chunks_meta = split_document("", chunk_size=500, overlap=50, pages=pages)
    if not all_chunks_meta:
        return 0

    chunks = [c["text"] for c in all_chunks_meta]

    all_embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        embs = get_embeddings(batch)
        all_embeddings.extend(embs)

    metadatas = [
        {
            "source": filename,
            "page": c.get("page", 1),
            "title_path": c.get("title_path", ""),
            "char_offset": c.get("char_offset", 0),
            "file_type": ext,
        }
        for c in all_chunks_meta
    ]
    chunk_count = add_documents(kb_id, chunks, all_embeddings, metadatas)

    file_size = os.path.getsize(filepath)
    file_mtime = os.path.getmtime(filepath)
    doc = Document(
        filename=filename,
        filepath=filepath,
        file_type=ext,
        file_size=file_size,
        file_mtime=file_mtime,
        chunk_count=chunk_count,
        kb_id=kb_id,
        uploaded_by=user_id,
    )
    db.add(doc)
    db.commit()
    return chunk_count


@router.post("/sync")
def sync_from_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    """扫描 uploads/ 文件夹，自动同步知识库。

    逻辑：
    1. 遍历 uploads/ 下的子目录（目录名 = 知识库 ID）
    2. 新目录 → 创建知识库 + 导入所有文件
    3. 已有知识库 → 对比文件：
       - 新文件 → 导入
       - 已修改文件（mtime/size 变化）→ 删除旧向量 + 重新导入
       - 已删除文件 → 清理 DB 记录 + 向量
    4. 数据库中有但目录已不存在 → 删除知识库（级联清理）
    """
    upload_root = settings.UPLOAD_DIR
    if not os.path.isdir(upload_root):
        return {"created": 0, "updated": 0, "removed": 0, "details": []}

    admin = db.query(User).filter(User.is_admin).first()
    if not admin:
        raise HTTPException(status_code=500, detail="没有管理员用户")
    user_id = admin.id

    created = 0
    updated = 0
    removed = 0
    details = []

    # 扫描 uploads/ 下的子目录
    existing_dirs = set()
    for entry in os.listdir(upload_root):
        entry_path = os.path.join(upload_root, entry)
        if os.path.isdir(entry_path) and entry.isdigit():
            existing_dirs.add(int(entry))

    # 1. 处理存在的目录
    for kb_id in sorted(existing_dirs):
        upload_dir = os.path.join(upload_root, str(kb_id))
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

        # 新知识库：目录存在但数据库没有
        if not kb:
            kb = KnowledgeBase(
                id=kb_id,
                name=f"知识库 {kb_id}",
                description=f"从 uploads/{kb_id}/ 自动导入",
                owner_id=user_id,
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)
            created += 1
            details.append(f"新建知识库 {kb_id}")

        # 收集磁盘上的文件（仅支持的类型）
        disk_files = {}
        for fname in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, fname)
            if not os.path.isfile(fpath):
                continue
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext in ALLOWED_TYPES:
                disk_files[fname] = {
                    "path": fpath,
                    "ext": ext,
                    "mtime": os.path.getmtime(fpath),
                    "size": os.path.getsize(fpath),
                }

        # 收集数据库中该知识库的文档记录
        db_docs = {d.filename: d for d in db.query(Document).filter(Document.kb_id == kb_id).all()}

        disk_names = set(disk_files.keys())
        db_names = set(db_docs.keys())

        # 新文件：磁盘有但数据库没有
        for fname in sorted(disk_names - db_names):
            info = disk_files[fname]
            try:
                n = _process_file(info["path"], fname, info["ext"], kb_id, user_id, db)
                updated += 1
                details.append(f"[KB {kb_id}] 新增 {fname} ({n} 切片)")
            except Exception as e:
                details.append(f"[KB {kb_id}] 新增 {fname} 失败: {e}")

        # 已删除文件：数据库有但磁盘没有
        for fname in sorted(db_names - disk_names):
            doc = db_docs[fname]
            try:
                delete_by_source(kb_id, fname)
                db.delete(doc)
                db.commit()
                removed += 1
                details.append(f"[KB {kb_id}] 删除 {fname}")
            except Exception as e:
                details.append(f"[KB {kb_id}] 删除 {fname} 失败: {e}")

        # 已修改文件：两边都有，检查 mtime 或 size 是否变化
        for fname in sorted(disk_names & db_names):
            info = disk_files[fname]
            doc = db_docs[fname]
            mtime_changed = abs(info["mtime"] - (doc.file_mtime or 0)) > 1.0
            size_changed = info["size"] != doc.file_size
            if mtime_changed or size_changed:
                try:
                    # 删除旧向量
                    delete_by_source(kb_id, fname)
                    # 重新处理
                    n = _process_file(info["path"], fname, info["ext"], kb_id, user_id, db)
                    # 删除旧 DB 记录（_process_file 已新建）
                    db.delete(doc)
                    db.commit()
                    updated += 1
                    details.append(f"[KB {kb_id}] 更新 {fname} ({n} 切片)")
                except Exception as e:
                    details.append(f"[KB {kb_id}] 更新 {fname} 失败: {e}")

    # 2. 清理：数据库中有但目录已不存在的知识库
    all_kbs = db.query(KnowledgeBase).all()
    for kb in all_kbs:
        if kb.id not in existing_dirs:
            try:
                delete_collection(kb.id)
                db.query(Conversation).filter(Conversation.kb_id == kb.id).delete()
                db.query(Document).filter(Document.kb_id == kb.id).delete()
                db.delete(kb)
                db.commit()
                removed += 1
                details.append(f"删除失效知识库 {kb.id}")
            except Exception as e:
                details.append(f"删除失效知识库 {kb.id} 失败: {e}")

    return {
        "created": created,
        "updated": updated,
        "removed": removed,
        "details": details,
    }
