"""文本向量化服务，使用本地 sentence-transformers 模型。"""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_CACHE_DIR = Path(__file__).resolve().parents[2] / "hf_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_CACHE_DIR))

MODEL_NAME = "shibing624/text2vec-base-chinese"
_model = SentenceTransformer(MODEL_NAME)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """将文本列表批量转换为 768 维向量。"""
    embeddings = _model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
