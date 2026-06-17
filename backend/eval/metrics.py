"""RAG 评估指标计算模块。

包含三类指标：
  1. 检索质量：Hit Rate, MRR, Recall, Precision, NDCG@K
  2. 生成质量：Faithfulness, Answer Relevancy, Context Precision/Recall (基于 Ragas)
  3. 端到端：延迟, 完整性, 拒答能力, 多轮连贯性
"""

import math
import time
from dataclasses import dataclass, field


# ============================================================
# 1. 检索质量指标
# ============================================================


def hit_rate(retrieved_ids: list[int], relevant_ids: set[int], top_k: int = 5) -> float:
    """Hit Rate@K: top-K 结果中是否至少命中一个相关文档。"""
    top = retrieved_ids[:top_k]
    return 1.0 if any(cid in relevant_ids for cid in top) else 0.0


def mean_reciprocal_rank(retrieved_ids: list[int], relevant_ids: set[int]) -> float:
    """MRR: 第一个相关文档的倒数排名。"""
    for i, cid in enumerate(retrieved_ids):
        if cid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(retrieved_ids: list[int], relevant_ids: set[int], top_k: int = 5) -> float:
    """Recall@K: top-K 结果中命中相关文档的比例。"""
    if not relevant_ids:
        return 0.0
    top = set(retrieved_ids[:top_k])
    return len(top & relevant_ids) / len(relevant_ids)


def precision_at_k(retrieved_ids: list[int], relevant_ids: set[int], top_k: int = 5) -> float:
    """Precision@K: top-K 结果中相关文档的比例。"""
    top = retrieved_ids[:top_k]
    if not top:
        return 0.0
    return sum(1 for cid in top if cid in relevant_ids) / len(top)


def ndcg_at_k(retrieved_ids: list[int], relevant_ids: set[int], top_k: int = 5) -> float:
    """NDCG@K: 归一化折损累积增益。"""
    dcg = 0.0
    for i, cid in enumerate(retrieved_ids[:top_k]):
        if cid in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)  # i+2 因为 rank 从 1 开始

    # 理想排序的 DCG
    ideal_count = min(len(relevant_ids), top_k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))

    return dcg / idcg if idcg > 0 else 0.0


@dataclass
class RetrievalMetrics:
    """单条查询的检索质量指标。"""
    hit_rate_3: float = 0.0
    hit_rate_5: float = 0.0
    mrr: float = 0.0
    recall_3: float = 0.0
    recall_5: float = 0.0
    precision_3: float = 0.0
    precision_5: float = 0.0
    ndcg_3: float = 0.0
    ndcg_5: float = 0.0


def compute_retrieval_metrics(
    retrieved_ids: list[int],
    relevant_ids: set[int],
) -> RetrievalMetrics:
    """计算单条查询的所有检索质量指标。"""
    return RetrievalMetrics(
        hit_rate_3=hit_rate(retrieved_ids, relevant_ids, 3),
        hit_rate_5=hit_rate(retrieved_ids, relevant_ids, 5),
        mrr=mean_reciprocal_rank(retrieved_ids, relevant_ids),
        recall_3=recall_at_k(retrieved_ids, relevant_ids, 3),
        recall_5=recall_at_k(retrieved_ids, relevant_ids, 5),
        precision_3=precision_at_k(retrieved_ids, relevant_ids, 3),
        precision_5=precision_at_k(retrieved_ids, relevant_ids, 5),
        ndcg_3=ndcg_at_k(retrieved_ids, relevant_ids, 3),
        ndcg_5=ndcg_at_k(retrieved_ids, relevant_ids, 5),
    )


@dataclass
class AggregatedRetrievalMetrics:
    """聚合后的检索质量指标。"""
    avg_hit_rate_3: float = 0.0
    avg_hit_rate_5: float = 0.0
    avg_mrr: float = 0.0
    avg_recall_3: float = 0.0
    avg_recall_5: float = 0.0
    avg_precision_3: float = 0.0
    avg_precision_5: float = 0.0
    avg_ndcg_3: float = 0.0
    avg_ndcg_5: float = 0.0
    total_queries: int = 0


def aggregate_retrieval_metrics(metrics_list: list[RetrievalMetrics]) -> AggregatedRetrievalMetrics:
    """聚合多条查询的检索质量指标（取平均）。"""
    n = len(metrics_list)
    if n == 0:
        return AggregatedRetrievalMetrics()

    def avg(fn):
        return sum(fn(m) for m in metrics_list) / n

    return AggregatedRetrievalMetrics(
        avg_hit_rate_3=avg(lambda m: m.hit_rate_3),
        avg_hit_rate_5=avg(lambda m: m.hit_rate_5),
        avg_mrr=avg(lambda m: m.mrr),
        avg_recall_3=avg(lambda m: m.recall_3),
        avg_recall_5=avg(lambda m: m.recall_5),
        avg_precision_3=avg(lambda m: m.precision_3),
        avg_precision_5=avg(lambda m: m.precision_5),
        avg_ndcg_3=avg(lambda m: m.ndcg_3),
        avg_ndcg_5=avg(lambda m: m.ndcg_5),
        total_queries=n,
    )


# ============================================================
# 2. 生成质量指标（简易版，无需 Ragas 外部依赖）
# ============================================================


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    """答案对关键词的覆盖率。"""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in answer.lower())
    return hits / len(keywords)


def faithfulness_simple(answer: str, context: str) -> float:
    """简易忠实度：答案中的实体/数字是否在上下文中出现。

    取答案中所有中文词和数字，检查在上下文中出现的比例。
    """
    import re

    # 提取答案中的关键信息（中文词组 + 数字/IP地址）
    answer_tokens = set(re.findall(r"[一-鿿]{2,}|[\d.]+(?:/\d+)?", answer))
    if not answer_tokens:
        return 0.0

    context_lower = context.lower()
    grounded = sum(1 for t in answer_tokens if t.lower() in context_lower)
    return grounded / len(answer_tokens)


def answer_relevancy_simple(answer: str, question: str) -> float:
    """简易答案相关性：答案与问题的关键词重叠度。"""
    import re

    q_tokens = set(re.findall(r"[一-鿿]{2,}", question))
    a_tokens = set(re.findall(r"[一-鿿]{2,}", answer))
    if not q_tokens:
        return 0.0

    overlap = q_tokens & a_tokens
    return len(overlap) / len(q_tokens)


def refusal_detection(answer: str) -> bool:
    """检测模型是否正确拒答（知识库中无相关信息时）。"""
    refusal_patterns = [
        "无法回答", "没有相关信息", "不在知识库", "知识库中没有",
        "无法找到", "没有找到", "未找到", "不包含", "没有提及",
        "无法提供", "无法确定", "不清楚", "没有足够信息",
        "cannot answer", "no relevant", "not found",
    ]
    answer_lower = answer.lower()
    return any(p in answer_lower for p in refusal_patterns)


@dataclass
class GenerationMetrics:
    """单条查询的生成质量指标。"""
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    keyword_coverage: float = 0.0
    answer_length: int = 0
    refusal_detected: bool = False
    refusal_correct: bool = False  # 应拒答时是否正确拒答


@dataclass
class AggregatedGenerationMetrics:
    """聚合后的生成质量指标。"""
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_keyword_coverage: float = 0.0
    avg_answer_length: float = 0.0
    refusal_accuracy: float = 0.0  # 拒答正确率
    total_queries: int = 0
    answerable_count: int = 0
    unanswerable_count: int = 0


# ============================================================
# 3. 端到端指标
# ============================================================


@dataclass
class E2EMetrics:
    """单条查询的端到端指标。"""
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    answer_length: int = 0
    context_length: int = 0
    num_chunks_retrieved: int = 0


@dataclass
class AggregatedE2EMetrics:
    """聚合后的端到端指标。"""
    avg_retrieval_latency_ms: float = 0.0
    avg_generation_latency_ms: float = 0.0
    avg_total_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p90_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_answer_length: float = 0.0
    avg_context_length: float = 0.0
    avg_chunks_retrieved: float = 0.0
    total_queries: int = 0


def aggregate_e2e_metrics(metrics_list: list[E2EMetrics]) -> AggregatedE2EMetrics:
    """聚合端到端指标。"""
    n = len(metrics_list)
    if n == 0:
        return AggregatedE2EMetrics()

    latencies = [m.total_latency_ms for m in metrics_list]
    latencies.sort()

    def percentile(data, p):
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]

    return AggregatedE2EMetrics(
        avg_retrieval_latency_ms=sum(m.retrieval_latency_ms for m in metrics_list) / n,
        avg_generation_latency_ms=sum(m.generation_latency_ms for m in metrics_list) / n,
        avg_total_latency_ms=sum(latencies) / n,
        p50_latency_ms=percentile(latencies, 50),
        p90_latency_ms=percentile(latencies, 90),
        p99_latency_ms=percentile(latencies, 99),
        avg_answer_length=sum(m.answer_length for m in metrics_list) / n,
        avg_context_length=sum(m.context_length for m in metrics_list) / n,
        avg_chunks_retrieved=sum(m.num_chunks_retrieved for m in metrics_list) / n,
        total_queries=n,
    )
