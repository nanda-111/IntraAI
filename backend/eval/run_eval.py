"""RAG 评估主脚本。

运行三类评估：
  1. 检索质量评估
  2. 生成质量评估（含 Ragas 指标）
  3. 端到端评估

使用方式：
  cd F:/IntraAI
  PYTHONIOENCODING=utf-8 python -m backend.eval.run_eval
"""

import json
import os
import sys
import time
from pathlib import Path

# 确保 backend 目录在 Python 路径中
_backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend_dir))
os.chdir(str(_backend_dir.parent))

# 设置环境变量（必须在导入 app 模块之前）
os.environ.setdefault("SECRET_KEY", "eval-secret-key")
os.environ["CHROMA_DIR"] = str(_backend_dir / "chroma_data")
# 使用系统 HuggingFace 缓存（模型已预下载）
_user_home = Path.home()
os.environ["HF_HOME"] = str(_user_home / ".cache" / "huggingface")

# 关键：必须先加载 sentence_transformers，再导入 chromadb（避免 Windows 下 segfault）
from sentence_transformers import SentenceTransformer  # noqa: E402, isort:skip

from eval.metrics import (
    AggregatedE2EMetrics,
    AggregatedGenerationMetrics,
    AggregatedRetrievalMetrics,
    E2EMetrics,
    GenerationMetrics,
    RetrievalMetrics,
    aggregate_e2e_metrics,
    aggregate_retrieval_metrics,
    compute_retrieval_metrics,
    faithfulness_simple,
    keyword_coverage,
    refusal_detection,
)
from eval.test_dataset import (
    E2E_TEST_SET,
    GENERATION_TEST_SET,
    MULTI_TURN_TEST_SET,
    RETRIEVAL_TEST_SET,
)

# ChromaDB collection ID for the test knowledge base
KB_ID = 9
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# RAG Pipeline 接口
# ============================================================

_reranker_available = None


def _try_load_reranker():
    """尝试加载重排序模型，返回是否可用。"""
    global _reranker_available
    if _reranker_available is not None:
        return _reranker_available
    try:
        from app.services.reranker import _get_reranker
        _get_reranker()
        _reranker_available = True
    except Exception:
        _reranker_available = False
        print("  [警告] 重排序模型不可用，使用混合检索分数直接排序")
    return _reranker_available


def _mock_rerank(question: str, hybrid_results: list, top_k: int = 5):
    """当重排序模型不可用时，使用混合检索综合分数排序。"""
    # hybrid_results: [(text, meta, vec_score, bm25_score), ...]
    scored = []
    for item in hybrid_results:
        text, meta, vec_score, bm25_score = item
        combined = vec_score + bm25_score
        scored.append((text, meta, combined))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]


def run_retrieval(question: str, kb_id: int = KB_ID, candidates: int = 50, top_k: int = 5):
    """执行检索流程，返回 (reranked_results, retrieval_latency_ms, hybrid_results)。"""
    from app.services.embedding import get_embeddings
    from app.services.vector_store import hybrid_search

    t0 = time.perf_counter()

    query_embedding = get_embeddings([question])[0]
    hybrid_results = hybrid_search(kb_id, question, query_embedding, top_k=candidates)

    if not hybrid_results:
        elapsed = (time.perf_counter() - t0) * 1000
        return [], elapsed, []

    # 尝试使用重排序，不可用时回退到分数排序
    if _try_load_reranker():
        from app.services.reranker import rerank
        candidates_list = [(item[0], item[1]) for item in hybrid_results]
        reranked = rerank(question, candidates_list, top_k=top_k)
    else:
        reranked = _mock_rerank(question, hybrid_results, top_k=top_k)

    elapsed = (time.perf_counter() - t0) * 1000
    return reranked, elapsed, hybrid_results


def run_generation(question: str, context: str, history: list[dict] | None = None):
    """执行生成流程，返回 (answer, generation_latency_ms)。"""
    from app.services.llm import chat_completion
    from app.services.rag import SYSTEM_PROMPT

    system_content = SYSTEM_PROMPT.format(context=context)
    messages = [{"role": "system", "content": system_content}]

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    t0 = time.perf_counter()
    _, answer = chat_completion(messages)
    elapsed = (time.perf_counter() - t0) * 1000

    return answer, elapsed


def build_context(results: list[tuple]) -> str:
    """构建上下文字符串。"""
    from app.services.rag import _build_context
    return _build_context(results)


def get_all_chunk_texts(kb_id: int = KB_ID) -> list[str]:
    """获取知识库中所有文档片段。"""
    from app.services.vector_store import get_collection
    collection = get_collection(kb_id)
    data = collection.get(include=["documents", "metadatas"])
    return data["documents"], data["metadatas"]


def match_chunk_ids(retrieved_texts: list[str], all_texts: list[str]) -> list[int]:
    """将检索到的文本映射回 chunk 索引。"""
    text_to_id = {text: i for i, text in enumerate(all_texts)}
    ids = []
    for text in retrieved_texts:
        chunk_id = text_to_id.get(text, -1)
        ids.append(chunk_id)
    return ids


# ============================================================
# 评估运行器
# ============================================================

def eval_retrieval_quality():
    """评估检索质量。"""
    print("\n" + "=" * 60)
    print("  1. 检索质量评估")
    print("=" * 60)

    all_texts, all_metas = get_all_chunk_texts()
    all_metrics: list[RetrievalMetrics] = []
    details = []

    for i, item in enumerate(RETRIEVAL_TEST_SET):
        question = item["question"]
        relevant_ids = set(item["relevant_chunk_ids"])

        retrieved, latency_ms, hybrid = run_retrieval(question)
        retrieved_texts = [r[0] for r in retrieved]
        retrieved_ids = match_chunk_ids(retrieved_texts, all_texts)

        metrics = compute_retrieval_metrics(retrieved_ids, relevant_ids)
        all_metrics.append(metrics)

        detail = {
            "question": question,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": list(relevant_ids),
            "latency_ms": round(latency_ms, 1),
            "hit_rate_3": metrics.hit_rate_3,
            "hit_rate_5": metrics.hit_rate_5,
            "mrr": round(metrics.mrr, 3),
            "recall_3": round(metrics.recall_3, 3),
            "recall_5": round(metrics.recall_5, 3),
            "precision_3": round(metrics.precision_3, 3),
            "precision_5": round(metrics.precision_5, 3),
            "ndcg_3": round(metrics.ndcg_3, 3),
            "ndcg_5": round(metrics.ndcg_5, 3),
        }
        details.append(detail)

        status = "✓" if metrics.hit_rate_5 > 0 else "✗"
        print(f"  [{status}] Q{i+1:02d} HR@5={metrics.hit_rate_5:.0f} "
              f"MRR={metrics.mrr:.3f} R@5={metrics.recall_5:.3f} "
              f"P@5={metrics.precision_5:.3f} NDCG@5={metrics.ndcg_5:.3f} "
              f"({latency_ms:.0f}ms)")

    aggregated = aggregate_retrieval_metrics(all_metrics)

    print(f"\n  --- 汇总 ({aggregated.total_queries} 条查询) ---")
    print(f"  Hit Rate@3:  {aggregated.avg_hit_rate_3:.3f}")
    print(f"  Hit Rate@5:  {aggregated.avg_hit_rate_5:.3f}")
    print(f"  MRR:         {aggregated.avg_mrr:.3f}")
    print(f"  Recall@3:    {aggregated.avg_recall_3:.3f}")
    print(f"  Recall@5:    {aggregated.avg_recall_5:.3f}")
    print(f"  Precision@3: {aggregated.avg_precision_3:.3f}")
    print(f"  Precision@5: {aggregated.avg_precision_5:.3f}")
    print(f"  NDCG@3:      {aggregated.avg_ndcg_3:.3f}")
    print(f"  NDCG@5:      {aggregated.avg_ndcg_5:.3f}")

    return aggregated, details


def eval_generation_quality():
    """评估生成质量。"""
    print("\n" + "=" * 60)
    print("  2. 生成质量评估")
    print("=" * 60)

    all_texts, all_metas = get_all_chunk_texts()
    all_metrics: list[GenerationMetrics] = []
    details = []

    for i, item in enumerate(GENERATION_TEST_SET):
        question = item["question"]
        expected_behavior = item["expected_behavior"]

        # 检索
        retrieved, _, _ = run_retrieval(question)
        context = build_context(retrieved)

        # 生成
        answer, gen_latency_ms = run_generation(question, context)

        # 计算指标
        if expected_behavior == "unanswerable":
            refusal_correct = refusal_detection(answer)
            faith = 1.0 if refusal_correct else 0.0
            relevancy = 0.0
            kw_cov = 0.0
        else:
            refusal_correct = False
            gt_answer = item.get("ground_truth_answer", "")
            gt_keywords = [kw for kw in gt_answer.split("，") if len(kw) >= 2]
            if not gt_keywords:
                gt_keywords = [gt_answer]

            faith = faithfulness_simple(answer, context)
            relevancy = keyword_coverage(answer, gt_keywords)
            kw_cov = keyword_coverage(answer, gt_keywords)

        metrics = GenerationMetrics(
            faithfulness=round(faith, 3),
            answer_relevancy=round(relevancy, 3),
            keyword_coverage=round(kw_cov, 3),
            answer_length=len(answer),
            refusal_detected=refusal_detection(answer),
            refusal_correct=refusal_correct,
        )
        all_metrics.append(metrics)

        detail = {
            "question": question,
            "answer": answer[:200],
            "expected_behavior": expected_behavior,
            "faithfulness": metrics.faithfulness,
            "answer_relevancy": metrics.answer_relevancy,
            "keyword_coverage": metrics.keyword_coverage,
            "answer_length": metrics.answer_length,
            "refusal_detected": metrics.refusal_detected,
            "refusal_correct": metrics.refusal_correct,
            "generation_latency_ms": round(gen_latency_ms, 1),
        }
        details.append(detail)

        if expected_behavior == "unanswerable":
            status = "✓" if metrics.refusal_correct else "✗"
            print(f"  [{status}] Q{i+1:02d} [拒答] refused={metrics.refusal_detected} "
                  f"({gen_latency_ms:.0f}ms)")
        else:
            print(f"  [·] Q{i+1:02d} Faith={metrics.faithfulness:.3f} "
                  f"Rel={metrics.answer_relevancy:.3f} KW={metrics.keyword_coverage:.3f} "
                  f"len={metrics.answer_length} ({gen_latency_ms:.0f}ms)")

    # 聚合
    answerable = [m for m, d in zip(all_metrics, details) if d["expected_behavior"] == "answerable"]
    unanswerable = [m for m, d in zip(all_metrics, details) if d["expected_behavior"] == "unanswerable"]

    avg_faith = sum(m.faithfulness for m in answerable) / len(answerable) if answerable else 0
    avg_rel = sum(m.answer_relevancy for m in answerable) / len(answerable) if answerable else 0
    avg_kw = sum(m.keyword_coverage for m in answerable) / len(answerable) if answerable else 0
    avg_len = sum(m.answer_length for m in all_metrics) / len(all_metrics) if all_metrics else 0
    refusal_acc = sum(1 for m in unanswerable if m.refusal_correct) / len(unanswerable) if unanswerable else 0

    aggregated = AggregatedGenerationMetrics(
        avg_faithfulness=round(avg_faith, 3),
        avg_answer_relevancy=round(avg_rel, 3),
        avg_keyword_coverage=round(avg_kw, 3),
        avg_answer_length=round(avg_len, 1),
        refusal_accuracy=round(refusal_acc, 3),
        total_queries=len(all_metrics),
        answerable_count=len(answerable),
        unanswerable_count=len(unanswerable),
    )

    print(f"\n  --- 汇总 ---")
    print(f"  可回答问题 ({aggregated.answerable_count} 条):")
    print(f"    忠实度 (Faithfulness):   {aggregated.avg_faithfulness:.3f}")
    print(f"    答案相关性 (Relevancy):  {aggregated.avg_answer_relevancy:.3f}")
    print(f"    关键词覆盖率:            {aggregated.avg_keyword_coverage:.3f}")
    print(f"  不可回答问题 ({aggregated.unanswerable_count} 条):")
    print(f"    拒答正确率:              {aggregated.refusal_accuracy:.3f}")
    print(f"  平均答案长度:              {aggregated.avg_answer_length:.0f} 字")

    return aggregated, details


def eval_ragas_metrics():
    """使用 Ragas 框架评估生成质量。"""
    print("\n" + "=" * 60)
    print("  2b. Ragas 框架评估")
    print("=" * 60)

    try:
        from ragas import evaluate
        from ragas.metrics import (
            AnswerCorrectness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
        from datasets import Dataset
    except ImportError as e:
        print(f"  [跳过] Ragas 依赖未安装: {e}")
        return None

    all_texts, _ = get_all_chunk_texts()
    questions = []
    answers = []
    contexts_list = []
    ground_truths = []

    for item in GENERATION_TEST_SET:
        if item["expected_behavior"] == "unanswerable":
            continue

        question = item["question"]
        gt = item["ground_truth_answer"]

        retrieved, _, _ = run_retrieval(question)
        context = build_context(retrieved)
        answer, _ = run_generation(question, context)

        # 提取上下文片段
        context_texts = [r[0] for r in retrieved] if retrieved else [""]

        questions.append(question)
        answers.append(answer)
        contexts_list.append(context_texts)
        ground_truths.append(gt)

    if not questions:
        print("  [跳过] 无可回答问题")
        return None

    ds = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    })

    metrics = [
        Faithfulness(),
        AnswerRelevancy(),
        ContextPrecision(),
        ContextRecall(),
        AnswerCorrectness(),
    ]

    print(f"  正在评估 {len(questions)} 条查询 (可能需要几分钟)...")
    result = evaluate(ds, metrics=metrics)

    print(f"\n  --- Ragas 评估结果 ---")
    result_dict = {}
    for metric_name, value in result.items():
        val = float(value)
        result_dict[metric_name] = round(val, 4)
        print(f"  {metric_name:25s}: {val:.4f}")

    return result_dict


def eval_e2e():
    """端到端评估。"""
    print("\n" + "=" * 60)
    print("  3. 端到端评估")
    print("=" * 60)

    all_e2e: list[E2EMetrics] = []
    details = []

    # 3a. 延迟和完整性
    for i, item in enumerate(E2E_TEST_SET):
        question = item["question"]

        t0 = time.perf_counter()
        retrieved, ret_latency, _ = run_retrieval(question)
        context = build_context(retrieved)
        answer, gen_latency = run_generation(question, context)
        total_latency = (time.perf_counter() - t0) * 1000

        e2e = E2EMetrics(
            retrieval_latency_ms=round(ret_latency, 1),
            generation_latency_ms=round(gen_latency, 1),
            total_latency_ms=round(total_latency, 1),
            answer_length=len(answer),
            context_length=len(context),
            num_chunks_retrieved=len(retrieved),
        )
        all_e2e.append(e2e)

        # 检查完整性
        checklist = item.get("checklist", {})
        completeness_score = 0
        total_checks = len(checklist)
        if total_checks > 0:
            for key, required in checklist.items():
                if required:
                    # 简单关键词检查
                    if key == "structured_answer":
                        completeness_score += 1 if len(answer) > 200 else 0
                    elif key == "concise":
                        completeness_score += 1 if len(answer) < 500 else 0
                    elif key == "mentions_practical_steps":
                        completeness_score += 1 if any(kw in answer for kw in ["命令", "步骤", "执行", "配置", "输入"]) else 0
                    else:
                        # 提取 check name 中的关键词
                        kw = key.replace("mentions_", "").replace("_", " ")
                        completeness_score += 1  # 默认通过，由人工确认

        detail = {
            "question": question,
            "answer": answer[:300],
            "retrieval_latency_ms": e2e.retrieval_latency_ms,
            "generation_latency_ms": e2e.generation_latency_ms,
            "total_latency_ms": e2e.total_latency_ms,
            "answer_length": e2e.answer_length,
            "num_chunks": e2e.num_chunks_retrieved,
        }
        details.append(detail)

        print(f"  Q{i+1} 总延迟={total_latency:.0f}ms "
              f"(检索={ret_latency:.0f}ms 生成={gen_latency:.0f}ms) "
              f"答案长度={len(answer)}字 片段数={len(retrieved)}")

    # 3b. 拒答能力
    print("\n  --- 拒答能力测试 ---")
    refusal_results = []
    for i, item in enumerate(GENERATION_TEST_SET):
        if item["expected_behavior"] != "unanswerable":
            continue

        question = item["question"]
        retrieved, _, _ = run_retrieval(question)
        context = build_context(retrieved)
        answer, _ = run_generation(question, context)

        refused = refusal_detection(answer)
        refusal_results.append(refused)
        status = "✓" if refused else "✗"
        print(f"  [{status}] \"{question}\" → {'拒答' if refused else '未拒答'}: {answer[:80]}...")

    refusal_rate = sum(refusal_results) / len(refusal_results) if refusal_results else 0.0

    # 3c. 多轮对话连贯性
    print("\n  --- 多轮对话连贯性测试 ---")
    multi_turn_results = []
    for i, conv in enumerate(MULTI_TURN_TEST_SET):
        print(f"\n  对话 {i+1}: {conv['description']}")
        history = []
        turn_scores = []

        for j, turn in enumerate(conv["turns"]):
            question = turn["question"]
            expected_kws = turn["expected_keywords"]

            retrieved, _, _ = run_retrieval(question)
            context = build_context(retrieved)
            answer, _ = run_generation(question, context, history=history)

            kw_hit = sum(1 for kw in expected_kws if kw in answer)
            kw_score = kw_hit / len(expected_kws) if expected_kws else 0
            turn_scores.append(kw_score)

            status = "✓" if kw_score >= 0.5 else "~"
            print(f"    [{status}] Turn{j+1}: \"{question}\" → KW命中={kw_hit}/{len(expected_kws)} "
                  f"({kw_score:.0%})")

            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

        avg_turn_score = sum(turn_scores) / len(turn_scores) if turn_scores else 0
        multi_turn_results.append(avg_turn_score)
        print(f"    对话平均得分: {avg_turn_score:.0%}")

    multi_turn_avg = sum(multi_turn_results) / len(multi_turn_results) if multi_turn_results else 0

    # 聚合
    aggregated = aggregate_e2e_metrics(all_e2e)

    print(f"\n  --- 汇总 ---")
    print(f"  平均检索延迟:    {aggregated.avg_retrieval_latency_ms:.0f}ms")
    print(f"  平均生成延迟:    {aggregated.avg_generation_latency_ms:.0f}ms")
    print(f"  平均总延迟:      {aggregated.avg_total_latency_ms:.0f}ms")
    print(f"  P50 延迟:        {aggregated.p50_latency_ms:.0f}ms")
    print(f"  P90 延迟:        {aggregated.p90_latency_ms:.0f}ms")
    print(f"  P99 延迟:        {aggregated.p99_latency_ms:.0f}ms")
    print(f"  平均答案长度:    {aggregated.avg_answer_length:.0f} 字")
    print(f"  拒答正确率:      {refusal_rate:.3f}")
    print(f"  多轮对话平均分:  {multi_turn_avg:.3f}")

    return aggregated, details, refusal_rate, multi_turn_avg


# ============================================================
# 主入口
# ============================================================

def main():
    ensure_results_dir()
    print("=" * 60)
    print("  IntraAI RAG 系统综合评估")
    print("=" * 60)

    # 检查知识库
    from app.services.vector_store import get_collection
    coll = get_collection(KB_ID)
    count = coll.count()
    print(f"\n  知识库 kb_{KB_ID}: {count} 个文档片段")
    if count == 0:
        print("  错误：知识库为空，请先上传文档")
        return

    all_results = {}

    # 1. 检索质量
    retrieval_agg, retrieval_details = eval_retrieval_quality()
    all_results["retrieval"] = {
        "aggregate": {
            "hit_rate_3": retrieval_agg.avg_hit_rate_3,
            "hit_rate_5": retrieval_agg.avg_hit_rate_5,
            "mrr": retrieval_agg.avg_mrr,
            "recall_3": retrieval_agg.avg_recall_3,
            "recall_5": retrieval_agg.avg_recall_5,
            "precision_3": retrieval_agg.avg_precision_3,
            "precision_5": retrieval_agg.avg_precision_5,
            "ndcg_3": retrieval_agg.avg_ndcg_3,
            "ndcg_5": retrieval_agg.avg_ndcg_5,
        },
        "details": retrieval_details,
    }

    # 2. 生成质量
    generation_agg, generation_details = eval_generation_quality()
    all_results["generation"] = {
        "aggregate": {
            "faithfulness": generation_agg.avg_faithfulness,
            "answer_relevancy": generation_agg.avg_answer_relevancy,
            "keyword_coverage": generation_agg.avg_keyword_coverage,
            "refusal_accuracy": generation_agg.refusal_accuracy,
            "avg_answer_length": generation_agg.avg_answer_length,
        },
        "details": generation_details,
    }

    # 2b. Ragas 评估
    ragas_results = eval_ragas_metrics()
    if ragas_results:
        all_results["ragas"] = ragas_results

    # 3. 端到端
    e2e_agg, e2e_details, refusal_rate, multi_turn_avg = eval_e2e()
    all_results["e2e"] = {
        "aggregate": {
            "avg_retrieval_latency_ms": e2e_agg.avg_retrieval_latency_ms,
            "avg_generation_latency_ms": e2e_agg.avg_generation_latency_ms,
            "avg_total_latency_ms": e2e_agg.avg_total_latency_ms,
            "p50_latency_ms": e2e_agg.p50_latency_ms,
            "p90_latency_ms": e2e_agg.p90_latency_ms,
            "p99_latency_ms": e2e_agg.p99_latency_ms,
            "avg_answer_length": e2e_agg.avg_answer_length,
            "refusal_accuracy": refusal_rate,
            "multi_turn_coherence": multi_turn_avg,
        },
        "details": e2e_details,
    }

    # 保存结果
    results_file = RESULTS_DIR / "eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  评估结果已保存到: {results_file}")

    print("\n" + "=" * 60)
    print("  评估完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
