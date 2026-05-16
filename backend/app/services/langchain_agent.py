"""LangChain Agent — 组装 Agent（LLM + Tools + Prompt）并提供执行接口。"""

import logging
from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage

from app.services.langchain_llm import get_mimo_llm
from app.services.langchain_tools import rag_search, db_query, web_search

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是一个智能助手，可以使用以下工具来回答用户问题：
1. 知识库检索 — 当问题涉及公司文档、规章制度、产品资料时使用
2. 数据库查询 — 当需要查询系统中的数据时使用
3. 网页搜索 — 当需要实时信息或外部知识时使用

请根据用户问题选择最合适的工具。如果不需要任何工具，可以直接回答。
回答请使用中文。"""

_agent_cache = None


def _get_agent():
    global _agent_cache
    if _agent_cache is None:
        llm = get_mimo_llm(streaming=True)
        _agent_cache = create_agent(
            llm,
            tools=[rag_search, db_query, web_search],
            system_prompt=AGENT_SYSTEM_PROMPT,
        )
    return _agent_cache


def _convert_history(history: list[dict] | None) -> list:
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
    agent = _get_agent()
    messages = _convert_history(history)
    messages.append(HumanMessage(content=question))

    result = agent.invoke({"messages": messages})
    last_message = result["messages"][-1]
    return last_message.content


async def run_agent_stream(
    question: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    agent = _get_agent()
    messages = _convert_history(history)
    messages.append(HumanMessage(content=question))

    async for event in agent.astream(
        {"messages": messages},
        stream_mode=["messages"],
    ):
        event_type, event_data = event
        if event_type == "messages" and event_data:
            chunk = event_data[0]
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
