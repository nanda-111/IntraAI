"""Ragas 框架独立评估脚本 - 使用项目 MiMo LLM。"""

import json
import os
import sys
import time
from pathlib import Path

os.environ["SECRET_KEY"] = "eval-secret-key"
os.environ["CHROMA_DIR"] = str(Path(__file__).resolve().parent.parent / "chroma_data")
os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

from sentence_transformers import SentenceTransformer  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KB_ID = 9
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def main():
    from eval.test_dataset import GENERATION_TEST_SET

    from app.core.config import settings
    from app.services.embedding import get_embeddings
    from app.services.llm import chat_completion
    from app.services.rag import SYSTEM_PROMPT, _build_context
    from app.services.vector_store import get_collection, hybrid_search

    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import (
        AnswerCorrectness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )
    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    print("=" * 60)
    print("  Ragas 框架评估 (使用 MiMo LLM)")
    print("=" * 60)

    # 配置 Ragas 使用的 LLM（通过 MiMo OpenAI-compatible API）
    llm = LangchainLLMWrapper(ChatOpenAI(
        model=settings.OPENAI_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_BASE_URL,
        temperature=0,
        max_tokens=2048,
    ))

    # 配置 embeddings（使用项目自带的 text2vec 模型包装为 LangChain 兼容）
    from langchain_core.embeddings import Embeddings

    class LocalText2VecEmbeddings(Embeddings):
        """将项目的 get_embeddings 包装为 LangChain Embeddings 接口。"""
        def embed_documents(self, texts):
            return get_embeddings(texts)
        def embed_query(self, text):
            return get_embeddings([text])[0]

    lc_embeddings = LangchainEmbeddingsWrapper(LocalText2VecEmbeddings())

    coll = get_collection(KB_ID)
    print(f"  知识库 kb_{KB_ID}: {coll.count()} 个文档片段")

    questions = []
    answers = []
    contexts_list = []
    ground_truths = []

    for i, item in enumerate(GENERATION_TEST_SET):
        if item["expected_behavior"] == "unanswerable":
            continue

        question = item["question"]
        gt = item["ground_truth_answer"]
        print(f"  [{i+1}] {question[:50]}...")

        query_embedding = get_embeddings([question])[0]
        hybrid_results = hybrid_search(KB_ID, question, query_embedding, top_k=50)

        if hybrid_results:
            scored = [(h[0], h[1], h[2] + h[3]) for h in hybrid_results]
            scored.sort(key=lambda x: x[2], reverse=True)
            top_results = scored[:5]
        else:
            top_results = []

        context = _build_context(top_results)
        context_texts = [r[0] for r in top_results] if top_results else [""]

        system_content = SYSTEM_PROMPT.format(context=context)
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]
        _, answer = chat_completion(messages)

        questions.append(question)
        answers.append(answer)
        contexts_list.append(context_texts)
        ground_truths.append(gt)

    print(f"\n  运行 Ragas 评估 ({len(questions)} 条, 需多次 LLM 调用)...")

    ds = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
    })

    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=lc_embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
        AnswerCorrectness(llm=llm, embeddings=lc_embeddings),
    ]

    t0 = time.perf_counter()
    result = evaluate(ds, metrics=metrics)
    elapsed = time.perf_counter() - t0

    print(f"\n  --- Ragas 结果 (耗时 {elapsed:.0f}s) ---")
    # Ragas 0.4.x: result.scores 是 list of dict, result[metric_name] 返回 list of scores
    result_dict = {}
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]:
        try:
            scores = result[metric_name]
            valid_scores = [s for s in scores if s is not None]
            avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
            result_dict[metric_name] = round(avg, 4)
            print(f"  {metric_name:25s}: {avg:.4f} ({len(valid_scores)}/{len(scores)} valid)")
        except Exception as e:
            print(f"  {metric_name:25s}: FAILED ({e})")
            result_dict[metric_name] = None

    # 保存
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ragas_file = RESULTS_DIR / "ragas_results.json"
    with open(ragas_file, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {ragas_file}")

    # 合并到主结果
    main_file = RESULTS_DIR / "eval_results.json"
    if main_file.exists():
        with open(main_file, encoding="utf-8") as f:
            all_results = json.load(f)
        all_results["ragas"] = result_dict
        with open(main_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"  已合并到: {main_file}")


if __name__ == "__main__":
    main()
