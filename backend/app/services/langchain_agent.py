"""LangChain Agent — 组装 Agent（LLM + Tools + Prompt）并提供执行接口。"""

import logging
from collections.abc import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

# Import tools first — triggers PyTorch/sentence-transformers loading.
# Must precede langchain_llm (OpenAI SDK) to avoid segfault on Windows.
from app.services.langchain_tools import db_query, rag_search, web_search
from app.services.langchain_llm import get_mimo_llm

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是一个智能助手，可以使用以下工具来回答用户问题：
1. 知识库检索 — 当问题涉及公司文档、规章制度、产品资料时使用
2. 数据库查询 — 当需要查询系统中的数据时使用
3. 网页搜索 — 当需要实时信息或外部知识时使用

请根据用户问题选择最合适的工具。如果不需要任何工具，可以直接回答。
回答请使用中文。"""


def _make_rag_tool(kb_id: int):
    """创建绑定了 kb_id 的知识库检索工具。"""

    def _bound_rag(query: str) -> str:
        return rag_search.invoke({"query": query, "kb_id": kb_id})

    _bound_rag.name = rag_search.name
    _bound_rag.description = rag_search.description
    _bound_rag.args_schema = rag_search.args_schema
    return _bound_rag


def _get_agent(kb_id: int = 1):
    llm = get_mimo_llm(streaming=True)
    tools = [_make_rag_tool(kb_id), db_query, web_search]
    return create_agent(
        llm,
        tools=tools,
        system_prompt=AGENT_SYSTEM_PROMPT,
    )


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


def run_agent(question: str, history: list[dict] | None = None, kb_id: int = 1) -> str:
    agent = _get_agent(kb_id)
    messages = _convert_history(history)
    messages.append(HumanMessage(content=question))

    result = agent.invoke({"messages": messages})
    last_message = result["messages"][-1]
    return last_message.content


async def run_agent_stream(
    question: str,
    history: list[dict] | None = None,
    kb_id: int = 1,
) -> AsyncIterator[str]:
    agent = _get_agent(kb_id)
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
                yield {"type": "answer", "content": chunk.content}
