"""
向量化服务模块

功能：将文本转换为向量（Embedding），用于语义搜索。

使用本地 sentence-transformers 模型（无需 API Key、无需联网）。
模型首次加载时会自动下载（约 90MB），之后从本地缓存加载。

使用方式：
    from app.services.embedding import get_embeddings
    vectors = get_embeddings(["你好世界", "今天天气不错"])
"""

from sentence_transformers import SentenceTransformer

# 加载本地 Embedding 模型
# 使用 all-MiniLM-L6-v2：体积小（约 90MB）、速度快、效果好
# 支持中英文，输出 384 维向量
# 首次运行时会自动从 HuggingFace 下载，之后使用本地缓存
model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    将文本列表批量转换为向量。

    工作原理：
      1. SentenceTransformer 将文本通过预训练的神经网络
      2. 网络输出固定维度的浮点数数组（向量）
      3. 语义相似的文本，向量在空间中距离更近

    参数：
        texts: 待转换的文本列表，如 ["你好", "世界"]

    返回：
        向量列表，每个向量是 384 维的浮点数列表
        如 [[0.1, -0.2, ...], [0.3, 0.4, ...]]
    """
    # model.encode() 批量处理文本，比逐条处理效率高很多
    embeddings = model.encode(texts)
    # numpy 数组转为 Python 列表（ChromaDB 需要列表格式）
    return embeddings.tolist()
