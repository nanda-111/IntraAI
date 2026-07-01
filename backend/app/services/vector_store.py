"""ChromaDB 向量存储 + BM25 混合检索服务。"""

import chromadb
import jieba
from rank_bm25 import BM25Okapi

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
    """纯向量检索（保留用于向后兼容）。"""
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


def _tokenize_chinese(text: str) -> list[str]:
    """中文分词（jieba），增强版：保留技术术语和命令。"""
    import re

    # jieba 精确模式分词
    tokens = jieba.lcut(text)

    # 保留：2+字符的中文词、英文单词/命令、IP地址、数字
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        # 保留中文词（2+字符）
        if re.match(r"^[一-鿿]{2,}$", t):
            result.append(t)
        # 保留英文单词/命令（2+字符）
        elif re.match(r"^[A-Za-z][A-Za-z0-9_./-]*$", t) and len(t) >= 2:
            result.append(t.lower())
        # 保留IP地址
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", t):
            result.append(t)
        # 保留数字（3+位，如端口号、密码等）
        elif re.match(r"^\d{3,}$", t):
            result.append(t)

    return result


def hybrid_search(
    kb_id: int,
    query: str,
    query_embedding: list[float],
    top_k: int = 50,
) -> list[tuple[str, dict, float, float]]:
    """混合检索：向量相似度 + BM25 关键词匹配，返回候选集。

    返回 [(text, metadata, vector_score, bm25_score), ...]，
    按 vector_score + bm25_score 综合排序，最多 top_k 条。
    """
    collection = get_collection(kb_id)
    count = collection.count()

    if count == 0:
        return []

    # ---------- 1. 向量检索 ----------
    vec_k = min(top_k, count)
    vec_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=vec_k,
        include=["documents", "metadatas", "distances"],
    )

    vec_docs = vec_results["documents"][0] if vec_results["documents"] else []
    vec_metas = vec_results["metadatas"][0] if vec_results.get("metadatas") else []
    vec_dists = vec_results["distances"][0] if vec_results.get("distances") else []

    # ChromaDB cosine distance → similarity
    vec_scores = [1.0 - d for d in vec_dists]

    # ---------- 2. BM25 关键词检索 ----------
    all_docs = collection.get(include=["documents", "metadatas"])
    corpus_texts = all_docs["documents"] or []
    corpus_metas = all_docs["metadatas"] or []

    corpus_tokens = [_tokenize_chinese(t) for t in corpus_texts]
    query_tokens = _tokenize_chinese(query)

    bm25 = BM25Okapi(corpus_tokens)
    bm25_raw_scores = bm25.get_scores(query_tokens)

    # 归一化 BM25 分数到 [0, 1]
    max_bm25 = float(bm25_raw_scores.max()) if len(bm25_raw_scores) > 0 else 1.0
    if max_bm25 > 0:
        bm25_norm = (bm25_raw_scores / max_bm25).tolist()
    else:
        bm25_norm = [0.0] * len(bm25_raw_scores)

    # 取 BM25 top_k
    bm25_indices = bm25_raw_scores.argsort()[-top_k:][::-1]

    # ---------- 3. 合并去重 ----------
    # text → {meta, vec_score, bm25_score}
    merged: dict[str, dict] = {}

    for i, text in enumerate(vec_docs):
        merged[text] = {
            "meta": vec_metas[i] if i < len(vec_metas) else {},
            "vec_score": vec_scores[i] if i < len(vec_scores) else 0.0,
            "bm25_score": 0.0,
        }

    for idx in bm25_indices:
        idx = int(idx)
        text = corpus_texts[idx]
        meta = corpus_metas[idx] if idx < len(corpus_metas) else {}
        bm25_score = bm25_norm[idx]

        if text in merged:
            merged[text]["bm25_score"] = max(merged[text]["bm25_score"], bm25_score)
        else:
            merged[text] = {
                "meta": meta,
                "vec_score": 0.0,
                "bm25_score": bm25_score,
            }

    # ---------- 4. 排序输出 ----------
    # 向量权重 0.6，BM25 权重 0.4（向量捕捉语义，BM25 捕捉关键词）
    VEC_WEIGHT = 0.6
    BM25_WEIGHT = 0.4

    results = [
        (text, info["meta"], info["vec_score"], info["bm25_score"]) for text, info in merged.items()
    ]
    results.sort(key=lambda x: x[2] * VEC_WEIGHT + x[3] * BM25_WEIGHT, reverse=True)

    return results[:top_k]
