"""ChromaDB 向量存储服务。"""

import chromadb

from app.core.config import settings

_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)


def get_collection(kb_id: int):
    """获取或创建知识库对应的向量集合，使用余弦相似度。"""
    return _client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(
    kb_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] | None = None,
):
    """将文档切片和向量批量存入 ChromaDB，返回写入数量。"""
    collection = get_collection(kb_id)
    existing = collection.count()

    ids = [f"chunk_{existing + i}" for i in range(len(chunks))]

    add_kwargs = {
        "ids": ids,
        "documents": chunks,
        "embeddings": embeddings,
    }
    if metadatas is not None:
        add_kwargs["metadatas"] = metadatas

    collection.add(**add_kwargs)
    return len(chunks)


def delete_by_source(kb_id: int, source: str):
    """删除知识库中指定来源文件的所有向量切片。"""
    collection = get_collection(kb_id)
    if collection.count() == 0:
        return
    collection.delete(where={"source": source})


def delete_collection(kb_id: int):
    """删除知识库对应的向量集合。"""
    try:
        _client.delete_collection(name=f"kb_{kb_id}")
    except Exception:
        pass  # 集合不存在时忽略


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[tuple[str, dict]]:
    """在知识库中检索最相关的文档切片，返回 [(文本, 元数据), ...]。"""
    collection = get_collection(kb_id)

    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas"],
    )

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results.get("metadatas") else []

    return [
        (doc, meta if meta else {})
        for doc, meta in zip(docs, metas or [{}] * len(docs), strict=False)
    ]
