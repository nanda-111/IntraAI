"""
向量化服务模块

功能：调用 OpenAI Embedding API，将文本转换为向量（Embedding）。

什么是向量（Embedding）？
  - 向量是文本的数学表示，用一串浮点数（如 1536 维）表示文本的语义信息
  - 语义相似的文本，它们的向量在空间中距离更近
  - 例如 "苹果手机" 和 "iPhone" 的向量会比 "苹果手机" 和 "汽车" 更接近
  - 向量使得计算机能够"理解"文本之间的语义关系

为什么需要向量化？
  - 传统搜索基于关键词匹配，无法理解语义（如搜"开心"找不到"高兴"）
  - 向量搜索基于语义相似度，能理解同义词和上下文
  - 这是 RAG（检索增强生成）系统的核心环节

使用方式：
    from app.services.embedding import get_embeddings
    vectors = get_embeddings(["你好世界", "今天天气不错"])
"""

from openai import OpenAI

from app.core.config import settings

# 创建 OpenAI 客户端实例
# api_key：API 密钥，用于身份验证
# base_url：API 基础地址，默认为 OpenAI 官方地址
#   可以替换为兼容的第三方 API 地址（如国内代理服务）
client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    调用 OpenAI Embedding API，将文本列表批量转换为向量。

    批量 vs 单条处理的效率区别：
      - 批量调用一次 API 请求处理多条文本，减少网络往返次数
      - 单条处理需要为每条文本单独发一次请求，效率低且浪费配额
      - OpenAI Embedding API 支持单次请求最多处理数千条文本
      - 因此我们在所有需要向量化的场景中都采用批量方式

    参数：
        texts: 待转换的文本列表，如 ["你好", "世界"]

    返回：
        向量列表，每个向量是一个浮点数列表
        如 [[0.1, -0.2, ...], [0.3, 0.4, ...]]
        向量维度取决于所使用的模型（text-embedding-3-small 为 1536 维）
    """
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    # response.data 是一个列表，每个元素对应一个输入文本
    # 每个元素的 .embedding 属性就是该文本的向量
    return [item.embedding for item in response.data]
