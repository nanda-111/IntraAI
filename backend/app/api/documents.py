"""
文档管理 API 路由

提供文档的上传、列表查询和删除接口。
文档归属于某个知识库（KnowledgeBase），是 RAG 系统的基础数据单元。

核心技术点：
  - UploadFile：FastAPI 的异步文件上传类型，底层使用 SpooledTemporaryFile，
    小文件在内存中处理，大文件自动溢写到磁盘，兼顾性能和内存安全。
  - await file.read()：UploadFile.read() 是异步方法，必须使用 await 调用。
    这是因为 FastAPI 运行在异步事件循环中，文件 I/O 操作需要非阻塞执行，
    否则会阻塞整个事件循环，影响服务器并发处理能力。
  - os.path.join()：跨平台路径拼接函数，自动使用当前操作系统的路径分隔符
    （Windows 用反斜杠 \\，Linux/macOS 用正斜杠 /），避免硬编码路径分隔符导致的兼容性问题。
"""

import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.schemas.document import DocumentOut

# 创建路由器，所有路由都以 /api/documents 为前缀
router = APIRouter(prefix="/api/documents", tags=["文档"])

# 允许上传的文件类型白名单
# 文件类型校验的安全意义：
#   1. 防止恶意文件上传：限制文件类型可以阻止用户上传可执行文件（.exe）、脚本文件等危险文件
#   2. 保证处理链路兼容性：后续的文档切片和向量化流程只支持这几种格式，
#      上传不支持的格式会导致处理失败
#   3. 减少存储浪费：避免用户上传无关的大文件（如视频、压缩包）
ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}


@router.post("/upload/{kb_id}", response_model=DocumentOut)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    上传文档到指定知识库。

    处理流程：
      1. 验证知识库存在性和用户权限
      2. 校验文件类型是否在允许列表中
      3. 将文件保存到本地磁盘（按知识库 ID 分目录存储）
      4. 在数据库中创建文档记录
    """
    # 1. 检查知识库是否存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 2. 权限检查：只有管理员或知识库所有者能上传文档
    # 这确保了用户不能向他人的知识库中添加内容
    if not current_user.is_admin and kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")

    # 3. 检查文件类型
    # 从文件名中提取扩展名并转为小写，确保大小写不敏感的匹配
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 4. 保存文件到本地目录
    # 按知识库 ID 创建子目录，实现文件隔离，便于后续按知识库管理和清理
    # os.path.join 自动使用操作系统对应的路径分隔符，保证跨平台兼容性
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb_id))
    os.makedirs(upload_dir, exist_ok=True)  # exist_ok=True 表示目录已存在时不报错
    filepath = os.path.join(upload_dir, file.filename)

    # 使用 await 异步读取文件内容
    # UploadFile.read() 是异步方法，必须用 await 调用。
    # 如果直接调用 file.read()（不加 await），会返回协程对象而非文件内容，
    # 并且在同步上下文中会导致运行时错误或数据错误。
    content = await file.read()

    with open(filepath, "wb") as f:
        f.write(content)

    # 5. 保存文档记录到数据库
    # chunk_count 暂时设为 0，后续 Task 3.4 会实现自动切片和向量化，
    # 届时会在处理完成后更新此字段
    doc = Document(
        filename=file.filename,
        filepath=filepath,
        file_type=ext,
        file_size=len(content),
        chunk_count=0,
        kb_id=kb_id,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)  # 刷新对象，获取数据库自动生成的字段（如 id、created_at）
    return doc


@router.get("/list/{kb_id}", response_model=list[DocumentOut])
def list_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取知识库下的所有文档列表。

    返回指定知识库中的全部文档元数据，用于前端展示文档管理界面。
    """
    # 先验证知识库是否存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    # 查询该知识库下的所有文档
    return db.query(Document).filter(Document.kb_id == kb_id).all()


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除文档（同时删除磁盘上的文件）。

    执行两步操作：
      1. 删除本地存储的原始文件
      2. 删除数据库中的文档记录
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 删除本地文件（先检查文件是否存在，避免文件已被手动删除时报错）
    if os.path.exists(doc.filepath):
        os.remove(doc.filepath)
    db.delete(doc)
    db.commit()
    return {"message": "已删除"}
