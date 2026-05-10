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
from app.services.vector_store import search
from app.services.llm import chat_completion, chat_completion_stream

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


def ask_with_rag(question: str, kb_id: int) -> str:
    """
    RAG 完整流程（非流式版本）。

    步骤：
      1. 将用户问题转换为向量（Embedding）
      2. 在知识库中检索最相关的文档片段
      3. 将检索到的片段拼接为上下文
      4. 构造 Prompt（系统提示 + 用户问题）
      5. 调用 LLM 生成回答

    参数：
        question: 用户的问题
        kb_id: 使用的知识库 ID

    返回：
        AI 的完整回答
    """
    # 步骤 1：问题向量化
    # 将用户的自然语言问题转换为向量，以便与知识库中的文档向量进行相似度比较
    # get_embeddings 返回的是列表（支持批量），这里只有一个问题，取第一个
    query_embedding = get_embeddings([question])[0]

    # 步骤 2：向量检索（取最相关的 5 个片段）
    # 在指定知识库中，找到与问题向量最相似的 top_k 个文档片段
    # 使用余弦相似度进行比较，返回相似度最高的文档文本
    chunks = search(kb_id, query_embedding, top_k=5)

    # 步骤 3：拼接上下文
    # 使用 "---" 作为分隔符将多个文档片段连接成一个字符串
    # 为什么用 "---" 分隔？
    #   - 清晰区分不同来源的文档片段，帮助 LLM 理解这是多段独立的内容
    #   - 比空行分隔更明显，避免 LLM 混淆片段的边界
    #   - 是一种常见的 Prompt Engineering 实践
    # 如果没有检索到任何片段（知识库为空或无相关内容），则使用占位文本
    context = "\n\n---\n\n".join(chunks) if chunks else "（无相关资料）"

    # 步骤 4：构造消息列表
    # 消息格式遵循 OpenAI Chat Completions API 的标准格式
    # system 消息：设定 AI 角色和行为规范，并嵌入检索到的上下文
    # user 消息：用户的原始问题
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]

    # 步骤 5：调用 LLM
    # 使用普通（非流式）调用，等待 LLM 完整生成回答后返回
    return chat_completion(messages)


def ask_with_rag_stream(question: str, kb_id: int):
    """
    RAG 完整流程（流式版本）。

    与 ask_with_rag 的区别：
      - 使用 chat_completion_stream 代替 chat_completion
      - 返回生成器，逐字输出回答
      - 前端可以通过 SSE 实现实时显示（类似打字效果）

    流式版本适用于聊天对话场景，用户可以实时看到 AI 的回复逐字出现，
    而不是等待几秒甚至十几秒后才看到完整回答。

    关于 yield from：
      - yield from 是 Python 的语法糖，用于将一个生成器的所有值委托给另一个生成器
      - 等价于：for chunk in chat_completion_stream(messages): yield chunk
      - 使用 yield from 的好处：
        1. 代码更简洁，不需要显式循环
        2. 语义更清晰，表示"将生成工作委托给被调用的生成器"
        3. 调用方可以透明地接收底层生成器产生的所有值
      - 这样 ask_with_rag_stream 本身也成为一个生成器函数，
        调用方可以用 for chunk in ask_with_rag_stream(...) 来逐个消费
    """
    # 步骤 1-3：与非流式版本相同
    # 向量化问题 → 检索相关文档 → 拼接上下文
    query_embedding = get_embeddings([question])[0]
    chunks = search(kb_id, query_embedding, top_k=5)
    context = "\n\n---\n\n".join(chunks) if chunks else "（无相关资料）"

    # 步骤 4：构造消息
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        {"role": "user", "content": question},
    ]

    # 步骤 5：流式调用 LLM
    # yield from 将 chat_completion_stream 生成器的所有增量文本
    # 逐个传递给 ask_with_rag_stream 的调用方
    # 前端收到每个 chunk 后可以立即渲染到界面上，实现实时打字效果
    yield from chat_completion_stream(messages)
