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


def add_documents(kb_id: int, chunks: list[str], embeddings: list[list[float]]):
    """
    将文档切片和对应的向量批量存入 ChromaDB。

    批量存储的优势：
      - 一次性写入多条数据，减少磁盘 I/O 操作次数
      - 相比逐条写入，批量操作效率提升显著
      - 在文档解析和切片阶段，一篇文档会被切成多个切片，
        批量存储能确保这些切片被高效地一起写入

    参数：
        kb_id: 知识库 ID
        chunks: 文本切片列表，如 ["切片内容1", "切片内容2"]
        embeddings: 对应的向量列表，如 [[0.1, ...], [0.2, ...]]
            chunks 和 embeddings 的长度必须一致，顺序一一对应

    返回：
        成功写入的切片数量

    工作原理：
      1. 获取该知识库的 Collection
      2. 获取当前已有的文档数量，生成不重复的 ID
         （如已有 3 条，则新 ID 为 chunk_3, chunk_4, ...）
      3. 调用 collection.add() 批量存储到向量数据库
    """
    collection = get_collection(kb_id)
    existing = collection.count()  # 获取当前集合中已有的记录数

    # 生成唯一 ID：基于已有数量偏移，避免与已有记录的 ID 冲突
    ids = [f"chunk_{existing + i}" for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,       # 原始文本（用于返回给用户查看检索结果）
        embeddings=embeddings,  # 向量数据（用于相似度计算和检索）
    )
    return len(chunks)


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[str]:
    """
    在知识库中检索与查询问题最相关的文档切片。

    这是 RAG 系统的核心检索环节：
      1. 用户提问 -> 将问题向量化（在调用方完成）
      2. 问题向量与知识库中所有文档向量进行相似度比较
      3. 返回最相似的 top_k 个文档切片
      4. 这些切片将作为上下文提供给大语言模型生成回答

    参数：
        kb_id: 知识库 ID
        query_embedding: 用户问题的向量表示
        top_k: 返回最相关的前 k 个结果（默认 5）

    返回：
        最相关的文本切片列表，按相似度从高到低排序

    工作原理：
      1. 获取知识库的 Collection
      2. 调用 collection.query() 进行相似度搜索
      3. ChromaDB 内部使用 HNSW 算法快速计算 query_embedding
         与所有存储向量的余弦距离
      4. 返回距离最近（最相似）的 top_k 个结果的原始文本
    """
    collection = get_collection(kb_id)

    # 如果集合为空，直接返回空列表，避免无效查询
    if collection.count() == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        # 确保 n_results 不超过集合中的文档数量
        n_results=min(top_k, collection.count()),
    )
    # results["documents"] 是二维列表：[[文档1, 文档2, ...]]
    # 因为我们只传入了一个 query_embedding，所以取第一个子列表
    return results["documents"][0] if results["documents"] else []
