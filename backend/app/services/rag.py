"""
RAG（检索增强生成）服务模块

功能：编排完整的 RAG 流程，将向量检索与大语言模型结合，实现基于知识库的智能问答。

什么是 RAG（Retrieval-Augmented Generation，检索增强生成）？
  - RAG 是一种结合"信息检索"和"文本生成"的 AI 架构模式
  - 核心思想：不要直接让 LLM 回答问题，而是先从知识库中检索相关资料，
    再将资料作为上下文提供给 LLM，让 LLM 根据资料生成回答
  - 这样做的好处：
    1. 减少幻觉（Hallucination）：LLM 容易编造看似合理但错误的信息，
       提供真实资料可以引导 LLM 基于事实回答
    2. 知识可更新：不需要重新训练模型，只需更新知识库即可让 AI 获取新知识
    3. 回答可溯源：可以追溯 AI 的回答是基于哪些资料生成的

为什么直接问 LLM 会有问题？
  - LLM 的知识截止于训练数据的日期，无法了解最新的信息
  - LLM 可能会"幻觉"（Hallucination），即自信地编造不存在的事实
  - LLM 无法访问企业内部的私有数据（如产品文档、规章制度等）
  - RAG 通过检索真实文档来解决这些问题

RAG 的完整流程：
  1. 用户提出问题
  2. 将问题转换为向量（Embedding）—— 语义表示
  3. 在向量数据库中检索与问题最相似的文档片段
  4. 将检索到的片段拼接为上下文（Context）
  5. 构造 Prompt：系统提示（含上下文）+ 用户问题
  6. 调用 LLM 生成基于上下文的回答

使用方式：
    from app.services.rag import ask_with_rag, ask_with_rag_stream

    # 非流式：获取完整回答
    answer = ask_with_rag("公司的请假制度是什么？", kb_id=1)

    # 流式：逐字获取回答（适用于 SSE 实时显示）
    for chunk in ask_with_rag_stream("公司的请假制度是什么？", kb_id=1):
        print(chunk, end="")
"""

from app.services.embedding import get_embeddings
from app.services.llm import chat_completion, chat_completion_stream
from app.services.vector_store import search

# RAG 的系统提示模板
# {context} 是占位符，会在运行时被替换为从知识库检索到的相关文档片段
#
# 设计意图：
#   - 第一句：明确 AI 的角色——企业内部知识助手，限定回答范围
#   - 要求 1：只根据资料回答，不要编造 → 减少幻觉，确保回答有据可查
#   - 要求 2：没有相关资料时明确告知 → 避免 AI 强行回答不相关的内容
#   - 要求 3：简洁专业 → 控制回答风格，避免冗长啰嗦
#   - 参考资料区域：将检索到的文档片段放在系统提示中，
#     让 AI 在生成回答时优先参考这些内容
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
    query_embedding = get_embeddings([question])[0]
    results = search(kb_id, query_embedding, top_k=5)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    # 如果有摘要，作为额外的系统消息插入
    if summary:
        messages.append(
            {
                "role": "system",
                "content": f"以下是对之前对话的摘要：\n{summary}",
            }
        )

    # 如果有历史对话，插入到当前问题之前
    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    # 最后追加当前问题
    messages.append({"role": "user", "content": question})

    return chat_completion(messages)


def ask_with_rag_stream(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
):
    query_embedding = get_embeddings([question])[0]
    results = search(kb_id, query_embedding, top_k=5)
    context = _build_context(results)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append(
            {
                "role": "system",
                "content": f"以下是对之前对话的摘要：\n{summary}",
            }
        )

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    yield from chat_completion_stream(messages)
