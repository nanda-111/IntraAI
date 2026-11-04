"""文本向量化服务，使用本地 sentence-transformers 模型。"""

import os

# 必须在导入 sentence_transformers 之前设置：
# huggingface_hub 在 import 时就会读取 HF_ENDPOINT，之后再设置不会生效，
# 导致国内直连 huggingface.co 超时（WinError 10060）。默认改走镜像。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from sentence_transformers import SentenceTransformer  # noqa: E402

MODEL_NAME = "shibing624/text2vec-base-chinese"
_model = SentenceTransformer(MODEL_NAME)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """将文本列表批量转换为 768 维向量。"""
    embeddings = _model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
