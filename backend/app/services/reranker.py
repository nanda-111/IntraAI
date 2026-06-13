"""重排序服务：使用 CrossEncoder 对候选文档进行精排。

模型：BAAI/bge-reranker-base（~278M 参数）
  - 中英双语支持，中文效果优秀
  - 比向量检索精度更高，但速度较慢（毫秒级）
  - 首次加载需从 HuggingFace 下载模型，之后从缓存读取
"""

import logging
import os
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_CACHE_DIR = Path(__file__).resolve().parents[2] / "hf_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_CACHE_DIR))

_reranker = None


def _get_reranker():
    """延迟加载 CrossEncoder 模型（首次调用时才加载，避免启动阻塞）。"""
    global _reranker
    if _reranker is None:
        logger.info("加载重排序模型: %s", settings.RERANK_MODEL)
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.RERANK_MODEL, max_length=512)
        logger.info("重排序模型加载完成")
    return _reranker


def rerank(
    question: str,
    candidates: list[tuple[str, dict]],
    top_k: int = 5,
) -> list[tuple[str, dict, float]]:
    """对候选文档重排序，返回评分最高的 top_k 条。

    Args:
        question: 用户问题
        candidates: [(text, metadata), ...] 候选文档列表
        top_k: 返回的文档数量

    Returns:
        [(text, metadata, score), ...] 按 score 降序排列
    """
    if not candidates:
        return []

    # 构造 [question, passage] 对
    pairs = [[question, text] for text, _ in candidates]

    reranker = _get_reranker()
    raw_scores = reranker.predict(pairs)

    # sigmoid 归一化到 [0, 1]
    import math

    scores = [1.0 / (1.0 + math.exp(-float(s))) for s in raw_scores]

    # 组合并排序
    scored = [(candidates[i][0], candidates[i][1], scores[i]) for i in range(len(candidates))]
    scored.sort(key=lambda x: x[2], reverse=True)

    return scored[:top_k]
