# LangChain 集成设计文档

## 概述

在现有 IntraAI 项目中并行引入 LangChain，新增 Agent 模式作为聊天的可选路径。现有代码（`llm.py`、`rag.py` 等）完全不动，LangChain 层独立新增。

## 目标

- 新增 LangChain 封装的 MiMo LLM 客户端
- 新增 3 个 Agent 工具：RAG 检索、数据库查询、DuckDuckGo 网页搜索
- 新增 Agent 模式端点，支持 SSE 流式输出
- 保持现有普通模式完全不变

## 架构

```
POST /api/chat/
  body: { question, kb_id, session_id, mode }
  
  mode="normal" (默认) → 现有 services/ 路径（不改动）
  mode="agent"         → services/langchain_agent.py（新增）
```

## 新增文件

### 1. `backend/app/services/langchain_llm.py`

LangChain 的 `ChatOpenAI` 封装，指向 MiMo：

```python
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_mimo_llm(temperature=0.7, streaming=False):
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )
```

**学习点：** `ChatOpenAI` 是 LangChain 对 OpenAI 兼容 API 的统一封装，MiMo 兼容 OpenAI 协议所以可以直接用。

### 2. `backend/app/services/langchain_tools.py`

定义 3 个 LangChain Tool：

```python
from langchain.tools import tool

@tool
def rag_search(query: str) -> str:
    """当用户询问与知识库文档相关的问题时，使用此工具搜索知识库。"""
    # 调用现有的 embedding + vector_store 搜索
    ...

@tool  
def db_query(sql: str) -> str:
    """当用户需要查询数据库信息时，使用此工具执行只读 SQL 查询。仅允许 SELECT 语句。"""
    # 安全校验 → 执行 SELECT → 返回结果
    ...

@tool
def web_search(query: str) -> str:
    """当用户需要查询实时信息、新闻、或知识库之外的内容时，使用此工具搜索互联网。"""
    from langchain_community.tools import DuckDuckGoSearchRun
    return DuckDuckGoSearchRun().run(query)
```

**学习点：** `@tool` 装饰器把普通函数变成 Agent 可调用的工具。docstring 非常重要——Agent 靠它来决定何时调用哪个工具。

### 3. `backend/app/services/langchain_agent.py`

Agent 组装 + 执行：

```python
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .langchain_llm import get_mimo_llm
from .langchain_tools import rag_search, db_query, web_search

def create_agent():
    llm = get_mimo_llm(streaming=True)
    tools = [rag_search, db_query, web_search]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能助手，可以检索知识库、查询数据库、搜索网页来回答用户问题。"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

async def run_agent(question: str, history: list) -> str:
    agent_executor = create_agent()
    result = await agent_executor.ainvoke({
        "input": question,
        "chat_history": history,
    })
    return result["output"]

async def run_agent_stream(question: str, history: list):
    agent_executor = create_agent()
    async for event in agent_executor.astream_events(
        {"input": question, "chat_history": history},
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield chunk.content
```

**学习点：**
- `create_openai_tools_agent` — 使用 OpenAI Function Calling 协议的 Agent
- `AgentExecutor` — Agent 的运行时，负责循环调用 LLM + 工具直到得到最终答案
- `MessagesPlaceholder` — 在 prompt 中预留位置插入对话历史和中间思考过程
- `astream_events` — Agent 的异步流式事件流

## 修改文件

### 1. `backend/app/schemas/chat.py`

`ChatRequest` 增加 `mode` 字段：

```python
class ChatRequest(BaseModel):
    question: str
    kb_id: Optional[int] = None
    session_id: Optional[int] = None
    mode: str = "normal"  # "normal" | "agent"
```

### 2. `backend/app/api/chat.py`

在 `chat()` 和 `chat_stream()` 路由中增加 mode 分支：

```python
if data.mode == "agent":
    # 走 LangChain Agent 路径
    from app.services.langchain_agent import run_agent
    ...
else:
    # 走现有路径（不变）
    ...
```

### 3. `backend/requirements.txt`

新增依赖：

```
langchain>=0.3.0
langchain-openai>=0.3.0
langchain-community>=0.3.0
duckduckgo-search>=7.0.0
```

## 数据库查询工具安全设计

`db_query` 工具只允许 SELECT 语句，防止 SQL 注入：

```python
@tool
def db_query(sql: str) -> str:
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return "错误：只允许 SELECT 查询"
    # 禁止危险关键词
    for kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]:
        if kw in sql_upper:
            return f"错误：禁止使用 {kw} 语句"
    # 用只读连接执行
    ...
```

## 学习路径

按顺序阅读/修改文件，逐步掌握 LangChain：

1. **`langchain_llm.py`** — 理解 Model 封装
2. **`langchain_tools.py`** — 理解 Tool 定义（@tool 装饰器 + docstring）
3. **`langchain_agent.py`** — 理解 Agent 组装（prompt + tools + executor）
4. **`api/chat.py`** — 理解如何接入 SSE 流式输出
