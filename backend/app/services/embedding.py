"""
向量化服务模块

功能：将文本转换为向量（Embedding），用于语义搜索。

使用 MiMo API（OpenAI 兼容接口）进行向量化，无需本地模型、无需访问 HuggingFace。

使用方式：
    from app.services.embedding import get_embeddings
    vectors = get_embeddings(["你好世界", "今天天气不错"])
"""

from openai import OpenAI

from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    将文本列表批量转换为向量。

    使用 OpenAI 兼容的 Embeddings API，通过 MiMo 服务进行向量化。

    参数：
        texts: 待转换的文本列表，如 ["你好", "世界"]

    返回：
        向量列表，每个向量是浮点数列表
    """
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
