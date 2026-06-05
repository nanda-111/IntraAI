"""RAG 服务：向量检索 + 上下文拼接 + LLM 生成。"""

from app.services.embedding import get_embeddings
from app.services.llm import chat_completion, chat_completion_stream
from app.services.vector_store import search

SYSTEM_PROMPT = """你是一个企业内部知识助手。根据以下参考资料回答用户的问题。

要求：
1. 只根据参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明"根据现有知识库，我无法回答这个问题"
3. 回答要简洁、专业

参考资料：
{context}
"""


def _build_context(results: list[tuple[str, dict]]) -> str:
    """将检索结果拼接为带来源标记的上下文。"""
    if not results:
        return "（无相关资料）"
    parts = []
    for text, meta in results:
        source = meta.get("source", "")
        if source:
            parts.append(f"[来源: {source}]\n{text}")
        else:
            parts.append(text)
    return "\n\n---\n\n".join(parts)


def ask_with_rag(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
) -> str:
    """非流式 RAG 问答。"""
    query_embedding = get_embeddings([question])[0]
    results = search(kb_id, query_embedding, top_k=5)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append(
            {"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"}
        )

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
    query_embedding = get_embeddings([question])[0]
    results = search(kb_id, query_embedding, top_k=5)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append(
            {"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"}
        )

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    yield from chat_completion_stream(messages)
