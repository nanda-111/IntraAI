"""RAG 评估脚本 v3 - 精简版，RAGAS + 自定义指标混合。

使用方式：
  cd F:/IntraAI/backend
  PYTHONIOENCODING=utf-8 python eval/run_eval_v3.py

设计思路：
- RAGAS 框架：answer_relevancy（MiMo 可跑通）
- 自定义指标：faithfulness、keyword_coverage、retrieval metrics
- 砍掉：跨知识库测试、对抗性测试、多轮对话
- 并行执行 LLM 调用
"""

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ["SECRET_KEY"] = "eval-secret-key"
os.environ["CHROMA_DIR"] = str(Path(__file__).resolve().parent.parent / "chroma_data")
os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

from sentence_transformers import SentenceTransformer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.metrics import (
    compute_retrieval_metrics,
    aggregate_retrieval_metrics,
    faithfulness_simple,
    keyword_coverage,
    refusal_detection,
)
from eval.test_dataset import (
    RETRIEVAL_TEST_SET,
    GENERATION_TEST_SET,
)

KB_ID = 4
RESULTS_DIR = Path(__file__).resolve().parent / "results"
MAX_WORKERS = 4  # 并发数


# ============================================================
# 工具函数
# ============================================================

def init():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from app.services.vector_store import get_collection
    coll = get_collection(KB_ID)
    count = coll.count()
    print(f"  知识库 kb_{KB_ID}: {count} 个文档片段")
    return count


def get_all_chunks():
    from app.services.vector_store import get_collection
    coll = get_collection(KB_ID)
    data = coll.get(include=["documents", "metadatas"])
    return data["documents"], data["metadatas"]


def run_retrieval(question, top_k=5):
    from app.services.embedding import get_embeddings
    from app.services.vector_store import hybrid_search

    t0 = time.perf_counter()
    query_embedding = get_embeddings([question])[0]
    hybrid_results = hybrid_search(KB_ID, question, query_embedding, top_k=50)

    if not hybrid_results:
        return [], (time.perf_counter() - t0) * 1000

    scored = [(h[0], h[1], h[2] + h[3]) for h in hybrid_results]
    scored.sort(key=lambda x: x[2], reverse=True)
    elapsed = (time.perf_counter() - t0) * 1000
    return scored[:top_k], elapsed


def run_generation(question, context):
    from app.services.llm import chat_completion
    from app.services.rag import SYSTEM_PROMPT

    system_content = SYSTEM_PROMPT.format(context=context)
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": question},
    ]
    t0 = time.perf_counter()
    _, answer = chat_completion(messages)
    elapsed = (time.perf_counter() - t0) * 1000
    return answer, elapsed


def build_context(results):
    from app.services.rag import _build_context
    return _build_context(results)


def match_chunk_ids(retrieved_texts, all_texts):
    text_to_id = {text: i for i, text in enumerate(all_texts)}
    return [text_to_id.get(t, -1) for t in retrieved_texts]


def extract_keywords(text):
    keywords = set()
    keywords.update(re.findall(r'[一-鿿]{2,8}', text))
    keywords.update(re.findall(r'[A-Za-z][A-Za-z0-9]{1,}', text))
    keywords.update(re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text))
    return list(keywords)


# ============================================================
# Phase 1: 检索质量
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
        category = item.get("category", "unknown")
        item_id = item.get("id", f"R{i+1:02d}")

        retrieved, latency = run_retrieval(question)
        retrieved_texts = [r[0] for r in retrieved]
        retrieved_ids = match_chunk_ids(retrieved_texts, all_texts)

        metrics = compute_retrieval_metrics(retrieved_ids, relevant_ids)
        all_metrics.append(metrics)

        detail = {
            "id": item_id, "category": category, "question": question,
            "latency_ms": round(latency, 1),
            "hit_rate_5": metrics.hit_rate_5, "mrr": round(metrics.mrr, 3),
            "recall_5": round(metrics.recall_5, 3), "ndcg_5": round(metrics.ndcg_5, 3),
        }
        details.append(detail)

        status = "✓" if metrics.hit_rate_5 > 0 else "✗"
        print(f"  [{status}] {item_id} HR@5={metrics.hit_rate_5:.0f} MRR={metrics.mrr:.3f} ({latency:.0f}ms)")

    agg = aggregate_retrieval_metrics(all_metrics)
    result = {
        "aggregate": {
            "hit_rate_5": round(agg.avg_hit_rate_5, 4),
            "mrr": round(agg.avg_mrr, 4),
            "recall_5": round(agg.avg_recall_5, 4),
            "ndcg_5": round(agg.avg_ndcg_5, 4),
        },
        "details": details,
    }

    print(f"\n  --- 汇总 ({agg.total_queries} 条) ---")
    print(f"  Hit Rate@5: {agg.avg_hit_rate_5:.4f}")
    print(f"  MRR:        {agg.avg_mrr:.4f}")
    print(f"  Recall@5:   {agg.avg_recall_5:.4f}")
    return result


# ============================================================
# Phase 2: 生成质量（并行 + RAGAS answer_relevancy）
# ============================================================

def _eval_single_generation(item):
    """评估单条生成质量。"""
    question = item["question"]
    expected = item["expected_behavior"]
    item_id = item.get("id", "G??")
    key_points = item.get("key_points", [])
    gt = item.get("ground_truth_answer", "")

    retrieved, ret_ms = run_retrieval(question)
    context = build_context(retrieved)
    answer, gen_ms = run_generation(question, context)

    if expected == "unanswerable":
        refused = refusal_detection(answer)
        return {
            "id": item_id, "expected": "unanswerable", "question": question,
            "answer": answer[:300], "refusal_correct": refused,
            "gen_latency_ms": round(gen_ms, 1),
        }
    else:
        faith = faithfulness_simple(answer, context)
        kw_cov = keyword_coverage(answer, key_points) if key_points else 0
        return {
            "id": item_id, "expected": expected, "question": question,
            "answer": answer[:300], "ground_truth": gt,
            "faithfulness": round(faith, 3), "keyword_coverage": round(kw_cov, 3),
            "answer_length": len(answer), "gen_latency_ms": round(gen_ms, 1),
            "context": context,  # 保留用于 RAGAS
        }


def run_ragas_relevancy(items_with_context):
    """运行 RAGAS answer_relevancy 指标。"""
    try:
        from app.core.config import settings
        from app.services.embedding import get_embeddings
        from ragas import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.metrics import AnswerRelevancy
        from datasets import Dataset
        from langchain_openai import ChatOpenAI
        from langchain_core.embeddings import Embeddings

        class ForceN1ChatOpenAI(ChatOpenAI):
            def generate(self, messages, stop=None, callbacks=None, **kwargs):
                kwargs["n"] = 1
                return super().generate(messages, stop=stop, callbacks=callbacks, **kwargs)
            async def agenerate(self, messages, stop=None, callbacks=None, **kwargs):
                kwargs["n"] = 1
                return await super().agenerate(messages, stop=stop, callbacks=callbacks, **kwargs)

        llm = LangchainLLMWrapper(ForceN1ChatOpenAI(
            model=settings.OPENAI_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            temperature=0, max_tokens=4096, request_timeout=120,
        ))

        class LocalEmbeddings(Embeddings):
            def embed_documents(self, texts): return get_embeddings(texts)
            def embed_query(self, text): return get_embeddings([text])[0]

        lc_embeddings = LangchainEmbeddingsWrapper(LocalEmbeddings())

        questions, answers, contexts_list, ground_truths = [], [], [], []
        for item in items_with_context:
            if item["expected"] == "unanswerable":
                continue
            questions.append(item["question"])
            answers.append(item["answer"])
            contexts_list.append([item.get("context", "")])
            ground_truths.append(item.get("ground_truth", ""))

        if not questions:
            return None

        ds = Dataset.from_dict({
            "question": questions, "answer": answers,
            "contexts": contexts_list, "ground_truth": ground_truths,
        })

        print(f"\n  运行 RAGAS answer_relevancy ({len(questions)} 条)...")
        t0 = time.perf_counter()
        result = evaluate(ds, metrics=[AnswerRelevancy(llm=llm, embeddings=lc_embeddings)])
        elapsed = time.perf_counter() - t0

        scores = result["answer_relevancy"]
        valid = [s for s in scores if s is not None and not math.isnan(s)]
        avg = sum(valid) / len(valid) if valid else 0.0
        print(f"  RAGAS answer_relevancy: {avg:.4f} ({len(valid)}/{len(scores)} valid, {elapsed:.0f}s)")
        return round(avg, 4)
    except Exception as e:
        print(f"  RAGAS 评估失败: {e}")
        return None


def phase_generation():
    print("\n" + "=" * 60)
    print("  Phase 2: 生成质量评估 (并行)")
    print("=" * 60)

    details = []
    answerable, unanswerable = [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_eval_single_generation, item): item for item in GENERATION_TEST_SET}
        for future in as_completed(futures):
            item = futures[future]
            try:
                detail = future.result()
                details.append(detail)
                if detail["expected"] == "unanswerable":
                    unanswerable.append(detail["refusal_correct"])
                    s = "✓" if detail["refusal_correct"] else "✗"
                    print(f"  [{s}] {detail['id']} [拒答] ({detail['gen_latency_ms']:.0f}ms)")
                else:
                    answerable.append(detail)
                    print(f"  [·] {detail['id']} Faith={detail['faithfulness']:.3f} KW={detail['keyword_coverage']:.3f} ({detail['gen_latency_ms']:.0f}ms)")
            except Exception as e:
                print(f"  [✗] {item.get('id','??')} 失败: {e}")

    details.sort(key=lambda d: d["id"])

    avg_faith = sum(d["faithfulness"] for d in answerable) / len(answerable) if answerable else 0
    avg_kw = sum(d["keyword_coverage"] for d in answerable) / len(answerable) if answerable else 0
    refusal_acc = sum(unanswerable) / len(unanswerable) if unanswerable else 0

    # RAGAS answer_relevancy
    ragas_relevancy = run_ragas_relevancy(details)

    result = {
        "aggregate": {
            "faithfulness": round(avg_faith, 4),
            "keyword_coverage": round(avg_kw, 4),
            "refusal_accuracy": round(refusal_acc, 4),
            "ragas_answer_relevancy": ragas_relevancy,
        },
        "details": [{k: v for k, v in d.items() if k != "context"} for d in details],
    }

    print(f"\n  --- 汇总 ---")
    print(f"  忠实度:       {avg_faith:.4f}")
    print(f"  关键词覆盖:   {avg_kw:.4f}")
    print(f"  拒答准确率:   {refusal_acc:.4f}")
    if ragas_relevancy:
        print(f"  RAGAS相关性:  {ragas_relevancy:.4f}")
    return result


# ============================================================
# 报告生成
# ============================================================

def generate_report(retrieval_result, generation_result):
    """生成 Markdown 报告。"""
    lines = []
    lines.append("# RAG 系统评估报告")
    lines.append("")
    lines.append(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    def grade(val, thresholds=(0.8, 0.6, 0.4)):
        if val >= thresholds[0]: return "优秀"
        if val >= thresholds[1]: return "良好"
        if val >= thresholds[2]: return "一般"
        return "待改进"

    def grade_latency(val, thresholds=(5000, 15000, 30000)):
        if val <= thresholds[0]: return "优秀"
        if val <= thresholds[1]: return "良好"
        if val <= thresholds[2]: return "一般"
        return "待优化"

    # 汇总表
    lines.append("## 评估汇总")
    lines.append("")
    lines.append("| 评估维度 | 指标 | 值 | 评价 |")
    lines.append("|---------|------|-----|------|")

    if retrieval_result:
        r = retrieval_result["aggregate"]
        for metric, label in [("hit_rate_5", "Hit Rate@5"), ("mrr", "MRR"), ("recall_5", "Recall@5")]:
            v = r[metric]
            lines.append(f"| 检索质量 | {label} | {v:.4f} | {grade(v)} |")

    if generation_result:
        g = generation_result["aggregate"]
        for metric, label in [("faithfulness", "忠实度"), ("keyword_coverage", "关键词覆盖")]:
            v = g[metric]
            lines.append(f"| 生成质量 | {label} | {v:.4f} | {grade(v)} |")
        v = g["refusal_accuracy"]
        lines.append(f"| 生成质量 | 拒答准确率 | {v:.4f} | {grade(v)} |")
        if g.get("ragas_answer_relevancy"):
            v = g["ragas_answer_relevancy"]
            lines.append(f"| RAGAS | 答案相关性 | {v:.4f} | {grade(v)} |")

    # 检索延迟
    if retrieval_result:
        latencies = [d["latency_ms"] for d in retrieval_result["details"]]
        avg_lat = sum(latencies) / len(latencies)
        lines.append(f"| 性能 | 检索延迟 | {avg_lat:.0f}ms | {grade_latency(avg_lat)} |")

    if generation_result:
        gen_lats = [d["gen_latency_ms"] for d in generation_result["details"]]
        avg_gen = sum(gen_lats) / len(gen_lats)
        lines.append(f"| 性能 | 生成延迟 | {avg_gen:.0f}ms | {grade_latency(avg_gen)} |")

    lines.append("")

    # 检索详情
    if retrieval_result:
        lines.append("## 检索质量详情")
        lines.append("")
        failed = [d for d in retrieval_result["details"] if d["hit_rate_5"] == 0]
        if failed:
            lines.append(f"**失败查询** ({len(failed)} 条 Hit Rate@5 = 0)：")
            lines.append("")
            for q in failed:
                lines.append(f"- **{q['id']}** [{q['category']}] {q['question']}")
            lines.append("")

    # 生成详情
    if generation_result:
        lines.append("## 生成质量详情")
        lines.append("")
        low_faith = [d for d in generation_result["details"]
                     if d.get("faithfulness") is not None and d["faithfulness"] < 0.5]
        if low_faith:
            lines.append(f"**低忠实度问题** ({len(low_faith)} 条 < 0.5)：")
            lines.append("")
            for q in low_faith:
                lines.append(f"- **{q['id']}** 忠实度={q['faithfulness']:.3f}: {q['question']}")
            lines.append("")

    # 改进建议
    lines.append("## 改进建议")
    lines.append("")
    suggestions = []
    if retrieval_result:
        r = retrieval_result["aggregate"]
        if r["hit_rate_5"] < 0.8:
            suggestions.append("- **检索质量**: Hit Rate@5 偏低，建议优化 embedding 模型或调整检索参数")
        if r["mrr"] < 0.5:
            suggestions.append("- **排序质量**: MRR 偏低，建议优化 reranker 或调整混合检索权重")
    if generation_result:
        g = generation_result["aggregate"]
        if g["faithfulness"] < 0.7:
            suggestions.append("- **忠实度**: 建议优化 prompt 或增加上下文约束")
        if g["refusal_accuracy"] < 0.9:
            suggestions.append("- **拒答能力**: 建议在 prompt 中增加拒答指令")
    if not suggestions:
        suggestions.append("- 系统表现良好，继续保持")
    lines.extend(suggestions)
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 主入口
# ============================================================

def main():
    print("=" * 60)
    print("  IntraAI RAG 系统评估 v4 (精简版)")
    print("=" * 60)

    count = init()
    if count == 0:
        print("  错误：知识库为空")
        return

    t_start = time.perf_counter()

    retrieval_result = None
    generation_result = None

    try:
        retrieval_result = phase_retrieval()
    except Exception as e:
        print(f"  [错误] 检索评估失败: {e}")
        import traceback; traceback.print_exc()

    try:
        generation_result = phase_generation()
    except Exception as e:
        print(f"  [错误] 生成评估失败: {e}")
        import traceback; traceback.print_exc()

    # 保存结果
    all_results = {}
    if retrieval_result:
        all_results["retrieval"] = retrieval_result
    if generation_result:
        all_results["generation"] = generation_result

    results_file = RESULTS_DIR / "eval_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {results_file}")

    # 生成报告
    report = generate_report(retrieval_result, generation_result)
    report_file = RESULTS_DIR / "RAG_Evaluation_Report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  报告已生成: {report_file}")

    total_time = time.perf_counter() - t_start
    print(f"\n  总耗时: {total_time:.0f}s ({total_time/60:.1f}分钟)")
    print("=" * 60)
    print("  评估完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
