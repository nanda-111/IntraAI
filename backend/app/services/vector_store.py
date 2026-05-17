"""
向量存储服务模块

功能：使用 ChromaDB 存储和检索文档向量。

什么是 ChromaDB？
  - ChromaDB 是一个开源的向量数据库，专门用于存储和检索向量数据
  - 它提供了高效的相似度搜索，能在大量向量中快速找到最相似的结果
  - 支持嵌入式运行（无需独立服务），适合中小型项目

核心概念：
  - Collection（集合）：类似关系数据库中的"表"，用于组织向量数据
    每个知识库对应一个独立的 Collection，名称为 kb_{id}
  - Document（文档）：存储的原始文本，用于在搜索结果中展示给用户
  - Embedding（向量）：文本的数学表示，用于计算相似度
  - ID：每条记录的唯一标识符

PersistentClient vs Client（持久化 vs 内存）：
  - PersistentClient：将数据持久化到本地磁盘目录
    优点：服务重启后数据不丢失，适合生产环境
    缺点：写入速度略慢于纯内存
  - Client（HttpClient）：数据存储在内存中
    优点：读写速度最快
    缺点：服务重启后数据丢失，适合临时/测试场景
  本项目使用 PersistentClient，确保知识库数据持久化。

使用方式：
    from app.services.vector_store import add_documents, search, get_collection
    add_documents(kb_id=1, chunks=["切片1", "切片2"], embeddings=[[...], [...]])
    results = search(kb_id=1, query_embedding=[...], top_k=5)
"""

import chromadb

from app.core.config import settings

# 创建 ChromaDB 持久化客户端
# path：数据存储目录，ChromaDB 会将所有向量数据保存在此目录下
# 服务重启后数据仍然存在，不会丢失
_client = chromadb.PersistentClient(path=settings.CHROMA_DIR)


def get_collection(kb_id: int):
    """
    获取或创建知识库对应的向量集合（Collection）。

    每个知识库拥有独立的 Collection，实现数据隔离。
    get_or_create_collection 方法的逻辑：
      - 如果名为 kb_{kb_id} 的集合已存在，则返回它
      - 如果不存在，则创建一个新集合并返回

    metadata={"hnsw:space": "cosine"} 指定使用余弦相似度计算距离。
    余弦相似度（Cosine Similarity）：
      - 衡量两个向量方向的相似程度，不考虑向量长度
      - 取值范围：-1 到 1
        - 1 表示方向完全相同（语义完全相似）
        - 0 表示方向正交（语义无关）
        - -1 表示方向相反（语义相反）
      - 计算公式：cos(θ) = (A·B) / (||A|| × ||B||)
      - 相比欧氏距离，余弦相似度对文本长度不敏感，更适合文本语义比较

    参数：
        kb_id: 知识库 ID

    返回：
        ChromaDB Collection 对象
    """
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
    """
    将文档切片和对应的向量批量存入 ChromaDB。

    参数：
        kb_id: 知识库 ID
        chunks: 文本切片列表
        embeddings: 对应的向量列表
        metadatas: 可选的元数据列表，每个元素是一个 dict，
                   如 [{"source": "员工手册.pdf"}, ...]

    返回：
        成功写入的切片数量
    """
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


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[tuple[str, dict]]:
    """
    在知识库中检索与查询问题最相关的文档切片。

    返回：
        列表，每项为 (文本, 元数据) 元组，按相似度从高到低排序。
        元数据包含 source（来源文件名）等信息，无元数据时返回空 dict。
    """
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
