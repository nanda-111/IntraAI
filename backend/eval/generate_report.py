"""生成 RAG 评估报告。

从 eval_results.json 生成 Markdown 格式的评估报告。
"""

import json
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_results():
    """加载评估结果。"""
    results_file = RESULTS_DIR / "eval_results.json"
    if not results_file.exists():
        print(f"错误：结果文件不存在: {results_file}")
        return None
    with open(results_file, encoding="utf-8") as f:
        return json.load(f)


def generate_report(results):
    """生成 Markdown 报告。"""
    report = []
    report.append("# RAG 系统评估报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # 汇总表格
    report.append("## 评估汇总")
    report.append("")
    report.append("| 评估维度 | 指标 | 值 | 评价 |")
    report.append("|---------|------|-----|------|")

    # 检索质量
    if "retrieval" in results:
        r = results["retrieval"]["aggregate"]
        hr5 = r["hit_rate_5"]
        mrr = r["mrr"]
        recall5 = r["recall_5"]

        def grade(val, thresholds=(0.8, 0.6, 0.4)):
            if val >= thresholds[0]:
                return "优秀"
            elif val >= thresholds[1]:
                return "良好"
            elif val >= thresholds[2]:
                return "一般"
            else:
                return "待改进"

        report.append(f"| 检索质量 | Hit Rate@5 | {hr5:.4f} | {grade(hr5)} |")
        report.append(f"| | MRR | {mrr:.4f} | {grade(mrr)} |")
        report.append(f"| | Recall@5 | {recall5:.4f} | {grade(recall5)} |")

    # 生成质量
    if "generation" in results:
        g = results["generation"]["aggregate"]
        faith = g["faithfulness"]
        kw = g["keyword_coverage"]
        refusal = g["refusal_accuracy"]

        report.append(f"| 生成质量 | 忠实度 | {faith:.4f} | {grade(faith)} |")
        report.append(f"| | 关键词覆盖 | {kw:.4f} | {grade(kw)} |")
        report.append(f"| | 拒答准确率 | {refusal:.4f} | {grade(refusal)} |")

    # 端到端
    if "e2e" in results:
        e = results["e2e"]["aggregate"]
        latency = e["avg_total_latency_ms"]
        mt = e["multi_turn_coherence"]

        def grade_latency(val, thresholds=(5000, 15000, 30000)):
            if val <= thresholds[0]:
                return "优秀"
            elif val <= thresholds[1]:
                return "良好"
            elif val <= thresholds[2]:
                return "一般"
            else:
                return "待优化"

        report.append(f"| 端到端 | 平均延迟 | {latency:.0f}ms | {grade_latency(latency)} |")
        report.append(f"| | 多轮连贯性 | {mt:.4f} | {grade(mt)} |")

    # 对抗性测试
    if "adversarial" in results:
        a = results["adversarial"]["aggregate"]
        adv_acc = a["accuracy"]
        report.append(f"| 对抗性测试 | 准确率 | {adv_acc:.4f} | {grade(adv_acc)} |")

    # 跨知识库测试
    if "cross_kb" in results:
        c = results["cross_kb"]["aggregate"]
        ck_acc = c["accuracy"]
        report.append(f"| 跨知识库 | 准确率 | {ck_acc:.4f} | {grade(ck_acc)} |")

    # RAGAS 指标
    if "ragas" in results:
        ragas = results["ragas"]
        import math
        for metric_name, label in [
            ("faithfulness", "RAGAS 忠实度"),
            ("answer_relevancy", "RAGAS 答案相关性"),
            ("context_precision", "RAGAS 上下文精确度"),
            ("context_recall", "RAGAS 上下文召回率"),
            ("answer_correctness", "RAGAS 答案正确性"),
        ]:
            val = ragas.get(metric_name)
            if val is not None and not math.isnan(val):
                report.append(f"| RAGAS | {label} | {val:.4f} | {grade(val)} |")
            else:
                report.append(f"| RAGAS | {label} | N/A | 评估失败 |")

    report.append("")

    # 检索质量详情
    if "retrieval" in results:
        report.append("## 检索质量详情")
        report.append("")

        # 按类别
        if "by_category" in results["retrieval"]:
            report.append("### 按问题类别")
            report.append("")
            report.append("| 类别 | 数量 | Hit Rate@5 | MRR | Recall@5 |")
            report.append("|------|------|------------|-----|----------|")
            for cat, stats in results["retrieval"]["by_category"].items():
                report.append(f"| {cat} | {stats['count']} | {stats['hit_rate_5']:.4f} | {stats['mrr']:.4f} | {stats['recall_5']:.4f} |")
            report.append("")

        # 按难度
        if "by_difficulty" in results["retrieval"]:
            report.append("### 按难度级别")
            report.append("")
            report.append("| 难度 | 数量 | Hit Rate@5 | MRR | Recall@5 |")
            report.append("|------|------|------------|-----|----------|")
            for diff, stats in results["retrieval"]["by_difficulty"].items():
                report.append(f"| {diff} | {stats['count']} | {stats['hit_rate_5']:.4f} | {stats['mrr']:.4f} | {stats['recall_5']:.4f} |")
            report.append("")

        # 失败查询分析
        report.append("### 失败查询分析")
        report.append("")
        failed_queries = [d for d in results["retrieval"]["details"] if d["hit_rate_5"] == 0]
        if failed_queries:
            report.append(f"共有 {len(failed_queries)} 条查询完全失败（Hit Rate@5 = 0）：")
            report.append("")
            for q in failed_queries:
                report.append(f"- **{q['id']}** [{q['category']}] {q['question']}")
            report.append("")
        else:
            report.append("所有查询均有命中（Hit Rate@5 > 0）")
            report.append("")

    # 生成质量详情
    if "generation" in results:
        report.append("## 生成质量详情")
        report.append("")

        # 按类别
        if "by_category" in results["generation"]:
            report.append("### 按问题类别")
            report.append("")
            report.append("| 类别 | 数量 | 忠实度 | 关键词覆盖 | 拒答准确率 |")
            report.append("|------|------|--------|-----------|-----------|")
            for cat, stats in results["generation"]["by_category"].items():
                faith = f"{stats['avg_faithfulness']:.4f}" if stats['avg_faithfulness'] is not None else "-"
                kw = f"{stats['avg_keyword_coverage']:.4f}" if stats['avg_keyword_coverage'] is not None else "-"
                refusal = f"{stats['refusal_accuracy']:.4f}" if stats['refusal_accuracy'] is not None else "-"
                report.append(f"| {cat} | {stats['count']} | {faith} | {kw} | {refusal} |")
            report.append("")

        # 低忠实度问题
        report.append("### 低忠实度问题（< 0.5）")
        report.append("")
        low_faith = [d for d in results["generation"]["details"]
                     if d.get("faithfulness") is not None and d["faithfulness"] < 0.5]
        if low_faith:
            for q in low_faith:
                report.append(f"- **{q['id']}** 忠实度={q['faithfulness']:.3f}: {q['question']}")
            report.append("")
        else:
            report.append("无低忠实度问题")
            report.append("")

    # 对抗性测试详情
    if "adversarial" in results:
        report.append("## 对抗性测试详情")
        report.append("")
        report.append("| ID | 问题 | 正确 | 说明 |")
        report.append("|-----|------|------|------|")
        for d in results["adversarial"]["details"]:
            status = "✓" if d["correct"] else "✗"
            report.append(f"| {d['id']} | {d['question'][:40]}... | {status} | {d['trap'][:30]}... |")
        report.append("")

    # 跨知识库测试详情
    if "cross_kb" in results:
        report.append("## 跨知识库测试详情")
        report.append("")
        report.append("| ID | 问题 | 期望知识库 | 关键词匹配 | 正确 |")
        report.append("|-----|------|-----------|-----------|------|")
        for d in results["cross_kb"]["details"]:
            status = "✓" if d["correct"] else "✗"
            report.append(f"| {d['id']} | {d['question'][:30]}... | {d['expected_kb']} | {d['keyword_match_rate']:.1%} | {status} |")
        report.append("")

    # RAGAS 框架评估详情
    if "ragas" in results:
        report.append("## RAGAS 框架评估详情")
        report.append("")
        ragas = results["ragas"]
        import math

        report.append("| 指标 | 值 | 说明 |")
        report.append("|------|-----|------|")

        metric_descriptions = {
            "faithfulness": "答案中可归因于上下文的陈述比例",
            "answer_relevancy": "答案与问题的相关程度",
            "context_precision": "相关文档在检索结果中的排序质量",
            "context_recall": "标准答案中的信息被上下文覆盖的比例",
            "answer_correctness": "答案与标准答案的语义匹配度",
        }

        for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]:
            val = ragas.get(metric_name)
            desc = metric_descriptions.get(metric_name, "")
            if val is not None and not math.isnan(val):
                report.append(f"| {metric_name} | {val:.4f} | {desc} |")
            else:
                report.append(f"| {metric_name} | N/A | 评估失败（MiMo 模型不支持复杂 JSON 输出） |")

        report.append("")
        report.append("> **注意**: RAGAS 评估使用 MiMo LLM 作为评判模型。由于 MiMo 模型对复杂结构化 JSON 输出的支持有限，")
        report.append("> 部分指标（faithfulness、context_precision、context_recall、answer_correctness）评估失败。")
        report.append("> 如需完整 RAGAS 评估，建议使用 GPT-4 或 DeepSeek-v4 等更强的模型作为评判 LLM。")
        report.append("")

    # 改进建议
    report.append("## 改进建议")
    report.append("")

    suggestions = []

    if "retrieval" in results:
        r = results["retrieval"]["aggregate"]
        if r["hit_rate_5"] < 0.8:
            suggestions.append("- **检索质量**: Hit Rate@5 偏低，建议优化 embedding 模型或调整检索参数")
        if r["mrr"] < 0.5:
            suggestions.append("- **排序质量**: MRR 偏低，建议优化 reranker 或调整混合检索权重")

    if "generation" in results:
        g = results["generation"]["aggregate"]
        if g["faithfulness"] < 0.7:
            suggestions.append("- **忠实度**: 建议优化 prompt 或增加上下文约束")
        if g["refusal_accuracy"] < 0.9:
            suggestions.append("- **拒答能力**: 建议在 prompt 中增加拒答指令")

    if "adversarial" in results:
        a = results["adversarial"]["aggregate"]
        if a["accuracy"] < 0.8:
            suggestions.append("- **幻觉防护**: 建议在 prompt 中增加'如果信息不在上下文中，请说明'的指令")

    if not suggestions:
        suggestions.append("- 系统表现良好，继续保持")

    report.extend(suggestions)
    report.append("")

    return "\n".join(report)


def main():
    """主入口。"""
    results = load_results()
    if results is None:
        return

    report = generate_report(results)

    # 保存报告
    report_file = RESULTS_DIR / "RAG_Evaluation_Report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"报告已生成: {report_file}")

    # 打印报告
    print("\n" + "=" * 60)
    print(report)


if __name__ == "__main__":
    main()
