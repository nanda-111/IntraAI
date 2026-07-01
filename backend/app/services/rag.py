"""RAG 服务：混合检索 + 重排序 + 上下文拼接 + LLM 生成。

检索流程：
  1. 用户问题 → embedding 向量化
  2. 混合检索：向量相似度 + BM25 关键词 → 50 个候选
  3. 重排序：CrossEncoder 精排 → 筛选 top 3~5
  4. 拼接上下文 → LLM 生成回答
"""

from app.services.embedding import get_embeddings
from app.services.llm import chat_completion, chat_completion_stream
from app.services.reranker import rerank
from app.services.vector_store import hybrid_search

# 检索参数
RETRIEVAL_CANDIDATES = 50  # 混合检索候选数
RERANK_TOP_K = 5  # 重排序后保留数

SYSTEM_PROMPT = """你是企业内部知识库助手。严格根据以下参考资料回答用户问题。

## 核心规则

1. **严格基于上下文**: 只使用参考资料中明确陈述的信息，不要推断、扩展或补充
2. **不要编造信息**: 如果参考资料没有相关信息，必须明确说明"根据现有知识库，我无法回答这个问题"
3. **保留原文表述**: 引用配置命令、IP地址、技术参数时，使用参考资料中的原始表述
4. **简洁专业**: 回答要简洁，直接回答问题，不要添加背景知识或推测

## 回答格式

- 先给出直接答案
- 如有配置命令，用代码块展示
- 如有多个步骤，用编号列表
- 不要添加"根据参考资料"等前缀

## 参考资料

{context}
"""

# 拒答关键词检测 - 用于辅助判断是否应该拒答
_UNANSWERABLE_INDICATORS = [
    "没有提到",
    "未提及",
    "未涉及",
    "文档中没有",
    "没有相关信息",
    "资料中没有",
    "未提供",
    "未说明",
    "未记录",
]


def _build_context(results: list[tuple[str, dict] | tuple[str, dict, float]]) -> str:
    """将检索结果拼接为带来源标记的上下文。"""
    if not results:
        return "（无相关资料）"
    parts = []
    for i, item in enumerate(results, 1):
        text, meta = item[0], item[1]
        if meta is None:
            meta = {}
        source = meta.get("source", "")
        if source:
            parts.append(f"[片段{i} - 来源: {source}]\n{text}")
        else:
            parts.append(f"[片段{i}]\n{text}")
    return "\n\n---\n\n".join(parts)


def retrieve_and_rerank(
    question: str,
    kb_id: int,
    candidates: int = RETRIEVAL_CANDIDATES,
    top_k: int = RERANK_TOP_K,
) -> list[tuple[str, dict, float]]:
    """混合检索 + 重排序的完整检索流程。

    Returns:
        [(text, metadata, rerank_score), ...] 精排后的 top_k 文档
    """
    # 1. 向量化问题
    query_embedding = get_embeddings([question])[0]

    # 2. 混合检索：向量 + BM25 → 候选集
    hybrid_results = hybrid_search(kb_id, question, query_embedding, top_k=candidates)

    if not hybrid_results:
        return []

    # 转为 (text, meta) 格式供 rerank 使用
    candidates_list = [(item[0], item[1]) for item in hybrid_results]

    # 3. 重排序：CrossEncoder 精排
    reranked = rerank(question, candidates_list, top_k=top_k)

    return reranked


def ask_with_rag(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
) -> str:
    """非流式 RAG 问答。"""
    results = retrieve_and_rerank(question, kb_id)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    _, answer = chat_completion(messages)
    return answer


def ask_with_rag_stream(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
):
    """流式 RAG 问答，yield {"type": ..., "content": ...}。"""
    results = retrieve_and_rerank(question, kb_id)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    yield from chat_completion_stream(messages)
