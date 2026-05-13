"""
LangChain Agent 模块

组装 Agent（LLM + Tools + Prompt）并提供执行接口。

学习点：
  - create_agent：新版 LangChain 的 Agent 创建函数
    传入 LLM、工具列表、系统提示，自动处理工具调用循环
  - Agent 运行时循环：
    1. 把用户消息 + 工具列表给 LLM
    2. LLM 决定：直接回答 or 调用某个工具
    3. 如果调用工具 → 执行工具 → 把结果给 LLM → 回到步骤 2
    4. 如果直接回答 → 返回最终答案
  - astream + stream_mode=["messages"]：逐 token 流式输出
"""

import logging
from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.services.langchain_llm import get_mimo_llm
from app.services.langchain_tools import rag_search, db_query, web_search

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是一个智能助手，可以使用以下工具来回答用户问题：
1. 知识库检索 — 当问题涉及公司文档、规章制度、产品资料时使用
2. 数据库查询 — 当需要查询系统中的数据时使用
3. 网页搜索 — 当需要实时信息或外部知识时使用

请根据用户问题选择最合适的工具。如果不需要任何工具，可以直接回答。
回答请使用中文。"""


def _build_agent():
    """
    组装 Agent。

    使用 create_agent 一步完成：
      - model: MiMo LLM（已启用流式）
      - tools: 3 个工具（RAG检索、数据库查询、网页搜索）
      - system_prompt: Agent 的角色描述

    create_agent 内部会自动构建 prompt 模板，不需要手动配置 MessagesPlaceholder。
    """
    llm = get_mimo_llm(streaming=True)
    return create_agent(
        llm,
        tools=[rag_search, db_query, web_search],
        system_prompt=AGENT_SYSTEM_PROMPT,
    )


def _convert_history(history: list[dict] | None) -> list:
    """
    将我们的 history 格式转为 LangChain 消息格式。

    我们的格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    LangChain 格式：[HumanMessage(...), AIMessage(...)]
    """
    if not history:
        return []

    converted = []
    for msg in history:
        if msg["role"] == "user":
            converted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            converted.append(AIMessage(content=msg["content"]))
    return converted


def run_agent(question: str, history: list[dict] | None = None) -> str:
    """
    执行 Agent（非流式），返回完整回答。

    参数：
        question: 用户问题
        history: 历史对话列表

    返回：
        Agent 的最终回答文本

    内部流程：
      1. 组装历史消息 + 当前问题
      2. 调用 agent.invoke()，Agent 自动循环调用工具直到得出最终回答
      3. 取最后一条消息（AI 的回答）返回
    """
    agent = _build_agent()
    messages = _convert_history(history)
    messages.append(HumanMessage(content=question))

    result = agent.invoke({"messages": messages})
    # result["messages"] 包含所有消息（用户、工具调用、AI回答等）
    # 最后一条是 AI 的最终回答
    last_message = result["messages"][-1]
    return last_message.content


async def run_agent_stream(
    question: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """
    执行 Agent（流式），逐 token yield 回答内容。

    使用 astream + stream_mode=["messages"] 获取流式消息块。

    流式事件格式：
      每个事件是一个 tuple: ("messages", (AIMessageChunk,))
      AIMessageChunk.content 包含当前 token 的增量文本

    只有 content 非空的 chunk 才 yield（过滤掉元数据 chunk）。
    """
    agent = _build_agent()
    messages = _convert_history(history)
    messages.append(HumanMessage(content=question))

    async for event in agent.astream(
        {"messages": messages},
        stream_mode=["messages"],
    ):
        # event 格式: ("messages", (AIMessageChunk, ...))
        event_type, event_data = event
        if event_type == "messages" and event_data:
            chunk = event_data[0]
            # 只处理 AI 的消息块，且有实际内容
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
