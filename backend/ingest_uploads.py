"""将 uploads/ 目录下已有的文件批量导入知识库。

用法：cd backend && python ingest_uploads.py
"""

import os
import sys

# 确保从 backend 目录运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.document_processor import extract_text_with_pages, split_document
from app.services.embedding import get_embeddings
from app.services.vector_store import add_documents

ALLOWED_TYPES = {"pdf", "docx", "txt", "md"}
BATCH_SIZE = 100  # 向量化每批数量


def ingest_file(db, filepath: str, filename: str, ext: str, kb_id: int, user_id: int):
    """处理单个文件并存入知识库。"""
    # 检查是否已导入
    existing = (
        db.query(Document).filter(Document.filename == filename, Document.kb_id == kb_id).first()
    )
    if existing:
        print(f"  [跳过] 已存在: {filename}")
        return

    print(f"  [处理] {filename} ...", end=" ", flush=True)

    # 1. 提取文本
    pages = extract_text_with_pages(filepath, ext)
    if not pages:
        print("无文本内容，跳过")
        return

    # 2. 切片
    all_chunks_meta = split_document("", chunk_size=500, overlap=50, pages=pages)
    if not all_chunks_meta:
        print("切片为空，跳过")
        return

    chunks = [c["text"] for c in all_chunks_meta]

    # 3. 分批向量化
    all_embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        embs = get_embeddings(batch)
        all_embeddings.extend(embs)

    # 4. 构建元数据并存入 ChromaDB
    metadatas = []
    for c in all_chunks_meta:
        metadatas.append(
            {
                "source": filename,
                "page": c.get("page", 1),
                "title_path": c.get("title_path", ""),
                "char_offset": c.get("char_offset", 0),
                "file_type": ext,
            }
        )
    chunk_count = add_documents(kb_id, chunks, all_embeddings, metadatas)

    # 5. 写入数据库记录
    file_size = os.path.getsize(filepath)
    doc = Document(
        filename=filename,
        filepath=filepath,
        file_type=ext,
        file_size=file_size,
        chunk_count=chunk_count,
        kb_id=kb_id,
        uploaded_by=user_id,
    )
    db.add(doc)
    db.commit()
    print(f"完成 ({chunk_count} 个切片)")


def main():
    kb_id = 1
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(kb_id))

    if not os.path.isdir(upload_dir):
        print(f"目录不存在: {upload_dir}")
        return

    # 收集待处理文件
    files = []
    for fname in sorted(os.listdir(upload_dir)):
        fpath = os.path.join(upload_dir, fname)
        if not os.path.isfile(fpath):
            continue
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        files.append((fpath, fname, ext))

    supported = [(p, n, e) for p, n, e in files if e in ALLOWED_TYPES]
    skipped = [(p, n, e) for p, n, e in files if e not in ALLOWED_TYPES]

    print(f"=== 批量导入 uploads/{kb_id}/ 到知识库 {kb_id} ===")
    print(f"共 {len(files)} 个文件，{len(supported)} 个可处理，{len(skipped)} 个跳过")
    if skipped:
        print(f"跳过的文件类型: {', '.join(sorted(set(e for _, _, e in skipped)))}")
    print()

    db = SessionLocal()
    try:
        # 查找管理员用户
        admin = db.query(User).filter(User.is_admin).first()
        if not admin:
            print("错误：没有管理员用户，请先注册一个管理员")
            return
        user_id = admin.id
        print(f"使用管理员: {admin.username} (id={user_id})")

        # 确保知识库存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            print(f"知识库 {kb_id} 不存在，自动创建...")
            kb = KnowledgeBase(
                id=kb_id, name="默认知识库", description="自动创建", owner_id=user_id
            )
            db.add(kb)
            db.commit()
            db.refresh(kb)
            print(f"已创建知识库: {kb.name} (id={kb.id})")

        for fpath, fname, ext in supported:
            try:
                ingest_file(db, fpath, fname, ext, kb_id, user_id)
            except Exception as e:
                print(f"  [错误] {fname}: {e}")

        print("\n=== 完成 ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
