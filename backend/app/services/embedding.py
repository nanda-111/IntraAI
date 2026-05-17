"""
向量化服务模块（本地模型版本）

功能：使用本地 sentence-transformers 模型将文本转换为向量，无需外部 API。

模型：shibing624/text2vec-base-chinese
  - 专为中文优化的 Embedding 模型
  - 向量维度：768
  - 模型大小约 400MB，首次使用时自动从 HuggingFace 下载
  - 之后从本地缓存加载，无需网络

使用方式：
    from app.services.embedding import get_embeddings
    vectors = get_embeddings(["你好世界", "今天天气不错"])
"""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

# 设置 HuggingFace 镜像（国内网络环境需要）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 模型缓存目录 — 固定在项目 backend/ 下，重启不丢失
_CACHE_DIR = Path(__file__).resolve().parents[2] / "hf_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_CACHE_DIR))

# 模型名称 —— 中文 Embedding 模型
MODEL_NAME = "shibing624/text2vec-base-chinese"

# 全局加载模型（只加载一次，后续调用直接复用）
# 首次运行会下载约 400MB 模型文件到 ~/.cache/huggingface/hub/
# 之后从缓存加载，几秒内完成
_model = SentenceTransformer(MODEL_NAME)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    将文本列表批量转换为向量。

    参数：
        texts: 待转换的文本列表，如 ["你好", "世界"]

    返回：
        向量列表，每个向量是 768 维的浮点数列表
    """
    embeddings = _model.encode(texts, normalize_embeddings=True)
    # encode 返回 numpy array，转为 Python list 以便 JSON 序列化
    return embeddings.tolist()
