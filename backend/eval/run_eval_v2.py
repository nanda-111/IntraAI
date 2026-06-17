"""RAG 评估脚本 v2 - 分阶段运行，增量保存结果。

使用方式：
  cd F:/IntraAI/backend
  PYTHONIOENCODING=utf-8 python eval/run_eval_v2.py
"""

import json
import os
import sys
import time
from pathlib import Path

# 环境设置
os.environ["SECRET_KEY"] = "eval-secret-key"
os.environ["CHROMA_DIR"] = str(Path(__file__).resolve().parent.parent / "chroma_data")
os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

# 关键：先加载 sentence_transformers 避免 segfault
from sentence_transformers import SentenceTransformer  # noqa: E402

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.metrics import (
    compute_retrieval_metrics,
    aggregate_retrieval_metrics,
    faithfulness_simple,
    keyword_coverage,
    refusal_detection,
    aggregate_e2e_metrics,
    E2EMetrics,
    GenerationMetrics,
)
from eval.test_dataset import (
    RETRIEVAL_TEST_SET,
    GENERATION_TEST_SET,
    MULTI_TURN_TEST_SET,
    E2E_TEST_SET,
)

KB_ID = 9
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def init():
    """初始化服务。"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from app.services.vector_store import get_collection
    coll = get_collection(KB_ID)
    count = coll.count()
    print(f"  知识库 kb_{KB_ID}: {count} 个文档片段")
    return count


def get_all_chunks():
    """获取所有文档片段。"""
    from app.services.vector_store import get_collection
    coll = get_collection(KB_ID)
    data = coll.get(include=["documents", "metadatas"])
    return data["documents"], data["metadatas"]


def run_retrieval(question, top_k=5):
    """执行检索，返回 (results, latency_ms, hybrid_results)。"""
    from app.services.embedding import get_embeddings
    from app.services.vector_store import hybrid_search

    t0 = time.perf_counter()
    query_embedding = get_embeddings([question])[0]
    hybrid_results = hybrid_search(KB_ID, question, query_embedding, top_k=50)

    if not hybrid_results:
        return [], (time.perf_counter() - t0) * 1000, []

    # 使用综合分数排序（不依赖 reranker）
    scored = []
    for item in hybrid_results:
        text, meta, vec_score, bm25_score = item
        scored.append((text, meta, vec_score + bm25_score))
    scored.sort(key=lambda x: x[2], reverse=True)

    elapsed = (time.perf_counter() - t0) * 1000
    return scored[:top_k], elapsed, hybrid_results


def run_generation(question, context, history=None):
    """执行生成，返回 (answer, latency_ms)。"""
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


def build_context(results):
    """构建上下文。"""
    from app.services.rag import _build_context
    return _build_context(results)


def match_chunk_ids(retrieved_texts, all_texts):
    """映射检索结果到 chunk 索引。"""
    text_to_id = {text: i for i, text in enumerate(all_texts)}
    return [text_to_id.get(t, -1) for t in retrieved_texts]


# ============================================================
# Phase 1: 检索质量评估
# ============================================================

def phase_retrieval():
    print("\n" + "=" * 60)
    print("  Phase 1: 检索质量评估")
    print("=" * 60)

    all_texts, _ = get_all_chunks()
    all_metrics = []
    details = []

    for i, item in enumerate(RETRIEVAL_TEST_SET):
        question = item["question"]
        relevant_ids = set(item["relevant_chunk_ids"])

        retrieved, latency, _ = run_retrieval(question)
        retrieved_texts = [r[0] for r in retrieved]
        retrieved_ids = match_chunk_ids(retrieved_texts, all_texts)

        metrics = compute_retrieval_metrics(retrieved_ids, relevant_ids)
        all_metrics.append(metrics)

        detail = {
            "question": question,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": list(relevant_ids),
            "latency_ms": round(latency, 1),
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
              f"({latency:.0f}ms)")

    agg = aggregate_retrieval_metrics(all_metrics)
    result = {
        "aggregate": {
            "hit_rate_3": round(agg.avg_hit_rate_3, 4),
            "hit_rate_5": round(agg.avg_hit_rate_5, 4),
            "mrr": round(agg.avg_mrr, 4),
            "recall_3": round(agg.avg_recall_3, 4),
            "recall_5": round(agg.avg_recall_5, 4),
            "precision_3": round(agg.avg_precision_3, 4),
            "precision_5": round(agg.avg_precision_5, 4),
            "ndcg_3": round(agg.avg_ndcg_3, 4),
            "ndcg_5": round(agg.avg_ndcg_5, 4),
        },
        "details": details,
    }

    print(f"\n  --- 汇总 ({agg.total_queries} 条查询) ---")
    print(f"  Hit Rate@3:  {agg.avg_hit_rate_3:.4f}")
    print(f"  Hit Rate@5:  {agg.avg_hit_rate_5:.4f}")
    print(f"  MRR:         {agg.avg_mrr:.4f}")
    print(f"  Recall@3:    {agg.avg_recall_3:.4f}")
    print(f"  Recall@5:    {agg.avg_recall_5:.4f}")
    print(f"  Precision@3: {agg.avg_precision_3:.4f}")
    print(f"  Precision@5: {agg.avg_precision_5:.4f}")
    print(f"  NDCG@3:      {agg.avg_ndcg_3:.4f}")
    print(f"  NDCG@5:      {agg.avg_ndcg_5:.4f}")

    return result


# ============================================================
# Phase 2: 生成质量评估
# ============================================================

def phase_generation():
    print("\n" + "=" * 60)
    print("  Phase 2: 生成质量评估")
    print("=" * 60)

    details = []
    answerable_metrics = []
    unanswerable_metrics = []

    for i, item in enumerate(GENERATION_TEST_SET):
        question = item["question"]
        expected = item["expected_behavior"]

        retrieved, _, _ = run_retrieval(question)
        context = build_context(retrieved)
        answer, gen_ms = run_generation(question, context)

        if expected == "unanswerable":
            refused = refusal_detection(answer)
            detail = {
                "question": question,
                "answer": answer[:300],
                "expected": "unanswerable",
                "refusal_detected": refused,
                "refusal_correct": refused,
                "gen_latency_ms": round(gen_ms, 1),
            }
            unanswerable_metrics.append(refused)
            status = "✓" if refused else "✗"
            print(f"  [{status}] Q{i+1:02d} [拒答] refused={refused} ({gen_ms:.0f}ms)")
        else:
            gt = item.get("ground_truth_answer", "")
            gt_keywords = [kw.strip() for kw in gt.replace("，", "。").replace("、", "。").split("。") if len(kw.strip()) >= 2]
            if not gt_keywords:
                gt_keywords = [gt]

            faith = faithfulness_simple(answer, context)
            kw_cov = keyword_coverage(answer, gt_keywords)

            detail = {
                "question": question,
                "answer": answer[:300],
                "expected": "answerable",
                "faithfulness": round(faith, 3),
                "keyword_coverage": round(kw_cov, 3),
                "answer_length": len(answer),
                "gen_latency_ms": round(gen_ms, 1),
            }
            answerable_metrics.append({"faith": faith, "kw": kw_cov})
            print(f"  [·] Q{i+1:02d} Faith={faith:.3f} KW={kw_cov:.3f} "
                  f"len={len(answer)} ({gen_ms:.0f}ms)")

        details.append(detail)

    avg_faith = sum(m["faith"] for m in answerable_metrics) / len(answerable_metrics) if answerable_metrics else 0
    avg_kw = sum(m["kw"] for m in answerable_metrics) / len(answerable_metrics) if answerable_metrics else 0
    refusal_acc = sum(unanswerable_metrics) / len(unanswerable_metrics) if unanswerable_metrics else 0

    result = {
        "aggregate": {
            "faithfulness": round(avg_faith, 4),
            "keyword_coverage": round(avg_kw, 4),
            "refusal_accuracy": round(refusal_acc, 4),
            "answerable_count": len(answerable_metrics),
            "unanswerable_count": len(unanswerable_metrics),
        },
        "details": details,
    }

    print(f"\n  --- 汇总 ---")
    print(f"  可回答 ({len(answerable_metrics)} 条): 忠实度={avg_faith:.4f}, 关键词覆盖={avg_kw:.4f}")
    print(f"  不可回答 ({len(unanswerable_metrics)} 条): 拒答正确率={refusal_acc:.4f}")

    return result


# ============================================================
# Phase 3: 端到端评估
# ============================================================

def phase_e2e():
    print("\n" + "=" * 60)
    print("  Phase 3: 端到端评估")
    print("=" * 60)

    # 3a. 延迟测试
    print("\n  --- 延迟与完整性 ---")
    e2e_list = []
    for i, item in enumerate(E2E_TEST_SET):
        question = item["question"]
        t0 = time.perf_counter()
        retrieved, ret_ms, _ = run_retrieval(question)
        context = build_context(retrieved)
        answer, gen_ms = run_generation(question, context)
        total_ms = (time.perf_counter() - t0) * 1000

        e2e = E2EMetrics(
            retrieval_latency_ms=round(ret_ms, 1),
            generation_latency_ms=round(gen_ms, 1),
            total_latency_ms=round(total_ms, 1),
            answer_length=len(answer),
            context_length=len(context),
            num_chunks_retrieved=len(retrieved),
        )
        e2e_list.append(e2e)
        print(f"  Q{i+1} 总延迟={total_ms:.0f}ms (检索={ret_ms:.0f}ms 生成={gen_ms:.0f}ms) "
              f"答案={len(answer)}字")

    # 3b. 拒答测试
    print("\n  --- 拒答能力 ---")
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

    refusal_rate = sum(refusal_results) / len(refusal_results) if refusal_results else 0

    # 3c. 多轮对话
    print("\n  --- 多轮对话连贯性 ---")
    multi_turn_scores = []
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
            print(f"    [{status}] Turn{j+1}: \"{question}\" → KW命中={kw_hit}/{len(expected_kws)} ({kw_score:.0%})")
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
        avg = sum(turn_scores) / len(turn_scores) if turn_scores else 0
        multi_turn_scores.append(avg)
        print(f"    对话平均: {avg:.0%}")

    multi_turn_avg = sum(multi_turn_scores) / len(multi_turn_scores) if multi_turn_scores else 0

    # 聚合延迟
    agg = aggregate_e2e_metrics(e2e_list)

    result = {
        "aggregate": {
            "avg_retrieval_latency_ms": round(agg.avg_retrieval_latency_ms, 1),
            "avg_generation_latency_ms": round(agg.avg_generation_latency_ms, 1),
            "avg_total_latency_ms": round(agg.avg_total_latency_ms, 1),
            "p50_latency_ms": round(agg.p50_latency_ms, 1),
            "p90_latency_ms": round(agg.p90_latency_ms, 1),
            "avg_answer_length": round(agg.avg_answer_length, 1),
            "refusal_accuracy": round(refusal_rate, 4),
            "multi_turn_coherence": round(multi_turn_avg, 4),
        },
    }

    print(f"\n  --- 汇总 ---")
    print(f"  平均总延迟:  {agg.avg_total_latency_ms:.0f}ms (P50={agg.p50_latency_ms:.0f}ms P90={agg.p90_latency_ms:.0f}ms)")
    print(f"  检索延迟:    {agg.avg_retrieval_latency_ms:.0f}ms")
    print(f"  生成延迟:    {agg.avg_generation_latency_ms:.0f}ms")
    print(f"  平均答案长度: {agg.avg_answer_length:.0f}字")
    print(f"  拒答正确率:  {refusal_rate:.4f}")
    print(f"  多轮连贯性:  {multi_turn_avg:.4f}")

    return result


# ============================================================
# 主入口
# ============================================================

def main():
    print("=" * 60)
    print("  IntraAI RAG 系统综合评估 v2")
    print("=" * 60)

    count = init()
    if count == 0:
        print("  错误：知识库为空")
        return

    all_results = {}

    # Phase 1
    try:
        all_results["retrieval"] = phase_retrieval()
    except Exception as e:
        print(f"  [错误] 检索评估失败: {e}")
        import traceback; traceback.print_exc()

    # Phase 2
    try:
        all_results["generation"] = phase_generation()
    except Exception as e:
        print(f"  [错误] 生成评估失败: {e}")
        import traceback; traceback.print_exc()

    # Phase 3
    try:
        all_results["e2e"] = phase_e2e()
    except Exception as e:
        print(f"  [错误] 端到端评估失败: {e}")
        import traceback; traceback.print_exc()

    # 保存结果
    results_file = RESULTS_DIR / "eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {results_file}")

    print("\n" + "=" * 60)
    print("  评估完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
