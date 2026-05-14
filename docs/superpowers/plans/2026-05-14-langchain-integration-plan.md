# LangChain 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 IntraAI 项目中并行引入 LangChain，新增 Agent 模式（RAG检索 + 数据库查询 + DuckDuckGo搜索），支持 SSE 流式输出，不改动现有代码。

**Architecture:** 新增 3 个 LangChain 服务文件，修改 schema 和 chat 路由增加 `mode` 参数分流。Agent 使用 `create_openai_tools_agent` + `AgentExecutor`，通过 `astream_events` 实现流式输出。

**Tech Stack:** langchain, langchain-openai, langchain-community, duckduckgo-search, FastAPI SSE

---

## 文件结构

| 操作 | 文件路径 | 用途 |
|------|----------|------|
| 新增 | `backend/app/services/langchain_llm.py` | LangChain MiMo LLM 封装 |
| 新增 | `backend/app/services/langchain_tools.py` | 3 个 Agent 工具定义 |
| 新增 | `backend/app/services/langchain_agent.py` | Agent 组装 + 执行 + 流式 |
| 修改 | `backend/app/schemas/chat.py` | ChatRequest 增加 mode 字段 |
| 修改 | `backend/app/api/chat.py` | chat() 和 chat_stream() 增加 agent 分支 |
| 修改 | `backend/requirements.txt` | 新增依赖 |

---

### Task 1: 安装 LangChain 依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

在文件末尾新增：

```
# LangChain
langchain>=0.3.0
langchain-openai>=0.3.0
langchain-community>=0.3.0
duckduckgo-search>=7.0.0
```

- [ ] **Step 2: 安装依赖**

Run: `cd F:/IntraAI/backend && pip install -r requirements.txt`
Expected: 所有包安装成功，无报错

- [ ] **Step 3: 验证安装**

Run: `python -c "import langchain; import langchain_openai; import langchain_community; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add langchain, langchain-openai, langchain-community, duckduckgo-search"
```

---

### Task 2: 创建 LangChain LLM 封装

**Files:**
- Create: `backend/app/services/langchain_llm.py`

**LangChain 知识点：**
- `ChatOpenAI` 是 LangChain 对 OpenAI 兼容 API 的统一模型封装
- 只要 API 兼容 OpenAI 协议（MiMo 就是），就能直接用 `base_url` 指向它
- `streaming=True` 启用流式，后续 Agent 的 `astream_events` 依赖此配置

- [ ] **Step 1: 创建 langchain_llm.py**

```python
"""
LangChain MiMo LLM 封装模块

使用 LangChain 的 ChatOpenAI 类对接小米 MiMo API（OpenAI 兼容接口）。

学习点：
  - ChatOpenAI：LangChain 对 OpenAI 兼容 LLM 的封装
    它内部管理 API 调用、消息格式转换、流式处理等细节
  - 通过 base_url 参数可以指向任何 OpenAI 兼容的 API 端点
  - streaming=True 让模型支持逐 token 输出，Agent 的流式功能依赖于此
"""

from langchain_openai import ChatOpenAI

from app.core.config import settings


def get_mimo_llm(temperature: float = 0.7, streaming: bool = False) -> ChatOpenAI:
    """
    获取封装了 MiMo API 的 LangChain LLM 实例。

    参数：
        temperature: 控制输出随机性（0.0~2.0），默认 0.7
        streaming: 是否启用流式输出，默认 False

    返回：
        ChatOpenAI 实例，可以像 LangChain 中的其他 LLM 一样使用

    用法示例：
        llm = get_mimo_llm()
        response = llm.invoke("你好")  # 普通调用

        llm = get_mimo_llm(streaming=True)
        for chunk in llm.stream("你好"):  # 流式调用
            print(chunk.content, end="")
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd F:/IntraAI/backend && python -c "from app.services.langchain_llm import get_mimo_llm; print(type(get_mimo_llm()))"`
Expected: 输出类似 `<class 'langchain_openai.chat_models.base.ChatOpenAI'>`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langchain_llm.py
git commit -m "feat: add LangChain MiMo LLM wrapper"
```

---

### Task 3: 创建 Agent 工具 — RAG 检索

**Files:**
- Create: `backend/app/services/langchain_tools.py`（本 Task 创建，后续 Task 追加工具）

**LangChain 知识点：**
- `@tool` 装饰器把普通 Python 函数变成 LangChain Tool
- Tool 的 **docstring** 非常重要：Agent 靠读取 docstring 来判断何时调用哪个工具
- 函数的参数类型标注（`str`）会自动成为 Tool 的参数 schema

- [ ] **Step 1: 创建 langchain_tools.py，只写 RAG 工具**

```python
"""
LangChain Agent 工具模块

定义 Agent 可调用的工具。每个工具用 @tool 装饰器定义。

学习点：
  - @tool 装饰器：将普通函数转为 LangChain Tool 对象
  - docstring = 工具描述：Agent 靠它决定何时调用此工具，所以要写清楚
    "什么时候用这个工具" + "这个工具做什么"
  - 函数参数 = 工具参数：类型标注会自动生成 JSON Schema 给 LLM
  - 返回值必须是 str：Agent 需要文本形式的结果来继续推理
"""

from langchain_core.tools import tool

from app.services.embedding import get_embeddings
from app.services.vector_store import search as vector_search


@tool
def rag_search(query: str) -> str:
    """当用户询问与知识库中的文档、资料、规章制度相关的问题时，使用此工具搜索知识库。
    输入应该是用户的原始问题，工具会自动向量化并在知识库中搜索最相关的内容。"""
    try:
        embeddings = get_embeddings([query])
        if not embeddings:
            return "向量化失败，无法搜索知识库。"
        chunks = vector_search(1, embeddings[0], top_k=5)  # 默认搜索 kb_id=1
        if not chunks:
            return "知识库中没有找到相关内容。"
        return "\n\n---\n\n".join(chunks)
    except Exception as e:
        return f"知识库搜索出错：{str(e)}"
```

- [ ] **Step 2: 验证工具可导入**

Run: `cd F:/IntraAI/backend && python -c "from app.services.langchain_tools import rag_search; print(rag_search.name, rag_search.description[:30])"`
Expected: 输出工具名称和描述前 30 字符

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langchain_tools.py
git commit -m "feat: add RAG search tool for LangChain agent"
```

---

### Task 4: 创建 Agent 工具 — 数据库查询

**Files:**
- Modify: `backend/app/services/langchain_tools.py`

**安全设计：**
- 只允许 SELECT 语句
- 禁止 DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE
- 结果限制最多 20 行，防止返回过多数据

- [ ] **Step 1: 在 langchain_tools.py 中追加 db_query 工具**

在文件末尾追加：

```python
from sqlalchemy import text
from app.core.database import SessionLocal


@tool
def db_query(sql: str) -> str:
    """当用户需要查询数据库中的数据时，使用此工具执行 SQL 查询。
    仅支持 SELECT 查询。可用于查询用户信息、统计数据、对话记录等。
    输入应该是完整的 SQL SELECT 语句。"""
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    # 安全校验：只允许 SELECT
    if not sql_upper.startswith("SELECT"):
        return "错误：只允许 SELECT 查询语句。"

    # 安全校验：禁止危险关键词
    for kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]:
        if kw in sql_upper:
            return f"错误：禁止使用 {kw} 语句。"

    try:
        db = SessionLocal()
        try:
            result = db.execute(text(sql_stripped))
            rows = result.fetchall()
            if not rows:
                return "查询结果为空。"
            # 获取列名
            columns = list(result.keys())
            # 限制最多 20 行
            rows = rows[:20]
            # 格式化为文本表格
            lines = [" | ".join(columns)]
            lines.append("-" * len(lines[0]))
            for row in rows:
                lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
            return "\n".join(lines)
        finally:
            db.close()
    except Exception as e:
        return f"数据库查询出错：{str(e)}"
```

- [ ] **Step 2: 验证工具可导入**

Run: `cd F:/IntraAI/backend && python -c "from app.services.langchain_tools import db_query; print(db_query.name)"`
Expected: 输出 `db_query`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langchain_tools.py
git commit -m "feat: add read-only DB query tool for LangChain agent"
```

---

### Task 5: 创建 Agent 工具 — DuckDuckGo 网页搜索

**Files:**
- Modify: `backend/app/services/langchain_tools.py`

- [ ] **Step 1: 在 langchain_tools.py 中追加 web_search 工具**

在文件末尾追加：

```python
from langchain_community.tools import DuckDuckGoSearchRun


@tool
def web_search(query: str) -> str:
    """当用户需要查询实时信息、新闻、天气、或知识库和数据库中没有的信息时，使用此工具搜索互联网。
    输入应该是简洁的搜索关键词或问题。"""
    try:
        search = DuckDuckGoSearchRun()
        result = search.run(query)
        if not result:
            return "未找到相关搜索结果。"
        return result
    except Exception as e:
        return f"网页搜索出错：{str(e)}"
```

- [ ] **Step 2: 验证工具可导入**

Run: `cd F:/IntraAI/backend && python -c "from app.services.langchain_tools import web_search; print(web_search.name)"`
Expected: 输出 `web_search`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langchain_tools.py
git commit -m "feat: add DuckDuckGo web search tool for LangChain agent"
```

---

### Task 6: 创建 Agent 组装与执行模块

**Files:**
- Create: `backend/app/services/langchain_agent.py`

**LangChain 知识点：**
- `create_openai_tools_agent`：使用 OpenAI Function Calling 协议的 Agent，让 LLM 决定调用哪个工具
- `AgentExecutor`：Agent 运行时，负责 循环 {LLM思考 → 选择工具 → 执行工具 → 看结果 → 继续} 直到得到最终答案
- `ChatPromptTemplate`：模板化 prompt，`MessagesPlaceholder` 在其中预留占位符
- `agent_scratchpad`：Agent 的"草稿纸"，存放中间推理过程（调了哪些工具、结果是什么）

- [ ] **Step 1: 创建 langchain_agent.py**

```python
"""
LangChain Agent 模块

组装 Agent（LLM + Tools + Prompt）并提供执行接口。

学习点：
  - create_openai_tools_agent：基于 OpenAI Function Calling 的 Agent
    LLM 看到所有工具的描述，自己决定调用哪个（或直接回答）
  - AgentExecutor：Agent 的运行时循环
    1. 把用户问题 + 工具列表给 LLM
    2. LLM 决定：直接回答 or 调用某个工具
    3. 如果调用工具 → 执行工具 → 把结果给 LLM → 回到步骤 2
    4. 如果直接回答 → 返回最终答案
  - MessagesPlaceholder("agent_scratchpad")：
    存放 Agent 的中间推理过程，让 LLM 看到自己之前做了什么
  - astream_events：异步流式事件流，可以捕获 Agent 的每个中间步骤和 LLM 的逐 token 输出
"""

import logging
from typing import AsyncIterator

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.services.langchain_llm import get_mimo_llm
from app.services.langchain_tools import rag_search, db_query, web_search

logger = logging.getLogger(__name__)

# Agent 的系统提示
# 告诉 Agent 它的身份和行为规范
AGENT_SYSTEM_PROMPT = """你是一个智能助手，可以使用以下工具来回答用户问题：
1. 知识库检索 — 当问题涉及公司文档、规章制度、产品资料时使用
2. 数据库查询 — 当需要查询系统中的数据时使用
3. 网页搜索 — 当需要实时信息或外部知识时使用

请根据用户问题选择最合适的工具。如果不需要任何工具，可以直接回答。
回答请使用中文。"""


def _build_agent() -> AgentExecutor:
    """
    组装 Agent 执行器。

    返回配置好的 AgentExecutor 实例。

    内部流程：
      1. 获取 MiMo LLM（启用流式）
      2. 准备工具列表
      3. 构建 Prompt 模板
      4. 用 create_openai_tools_agent 组装 Agent
      5. 用 AgentExecutor 包装，设置最大迭代次数防止无限循环
    """
    llm = get_mimo_llm(streaming=True)
    tools = [rag_search, db_query, web_search]

    # Prompt 模板解释：
    # ("system", ...) — 系统消息，设定 Agent 角色
    # MessagesPlaceholder("chat_history") — 插入历史对话（由调用方传入）
    # ("human", "{input}") — 用户当前的问题
    # MessagesPlaceholder("agent_scratchpad") — Agent 的中间推理过程（自动填充）
    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,           # 打印 Agent 的推理过程（开发调试用）
        max_iterations=5,       # 最多循环 5 次，防止无限循环
        handle_parsing_errors=True,  # 解析错误时自动重试
    )


def _convert_history(history: list[dict] | None) -> list:
    """
    将我们的 history 格式转为 LangChain 消息格式。

    我们的格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    LangChain 格式：[HumanMessage(...), AIMessage(...)]
    """
    if not history:
        return []

    from langchain_core.messages import HumanMessage, AIMessage

    converted = []
    for msg in history:
        if msg["role"] == "user":
            converted.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            converted.append(AIMessage(content=msg["content"]))
    return converted


async def run_agent(question: str, history: list[dict] | None = None) -> str:
    """
    执行 Agent（非流式），返回完整回答。

    参数：
        question: 用户问题
        history: 历史对话列表

    返回：
        Agent 的最终回答文本
    """
    agent_executor = _build_agent()
    result = await agent_executor.ainvoke({
        "input": question,
        "chat_history": _convert_history(history),
    })
    return result["output"]


async def run_agent_stream(
    question: str,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """
    执行 Agent（流式），逐 token yield 回答内容。

    使用 astream_events 获取流式事件，只提取 LLM 生成的文本增量。

    astream_events 的事件类型：
      - "on_chat_model_stream"：LLM 生成了新的 token
      - "on_tool_start"：Agent 开始调用某个工具
      - "on_tool_end"：工具调用完成
      - "on_chain_start/end"：Agent 执行链的开始/结束

    我们只关心 "on_chat_model_stream"，因为它包含最终回答的文本增量。
    其他事件（工具调用等）可以用于前端显示"正在搜索..."等状态，但当前只返回文本。
    """
    agent_executor = _build_agent()

    async for event in agent_executor.astream_events(
        {"input": question, "chat_history": _convert_history(history)},
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield chunk.content
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd F:/IntraAI/backend && python -c "from app.services.langchain_agent import run_agent, run_agent_stream; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/langchain_agent.py
git commit -m "feat: add LangChain agent with streaming support"
```

---

### Task 7: 修改 ChatRequest Schema

**Files:**
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: 给 ChatRequest 增加 mode 字段**

在 `session_id` 行后面追加 `mode` 字段：

```python
class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None
    mode: str = "normal"  # "normal" 走现有流程，"agent" 走 LangChain Agent
```

- [ ] **Step 2: 验证 schema**

Run: `cd F:/IntraAI/backend && python -c "from app.schemas.chat import ChatRequest; r = ChatRequest(question='test'); print(r.mode)"`
Expected: 输出 `normal`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "feat: add mode field to ChatRequest for agent mode"
```

---

### Task 8: 修改 chat 路由 — 普通对话接口

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 在 chat() 函数中增加 agent 模式分支**

将 `chat()` 函数（第 134-164 行）改为：

```python
@router.post("/", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通对话接口（支持多轮上下文）"""
    session = None
    summary = None
    history = None

    if data.session_id:
        session, summary, history = _load_session_history(data.session_id, db)

    # Agent 模式
    if data.mode == "agent":
        import asyncio
        from app.services.langchain_agent import run_agent as agent_run
        # 非流式 Agent 调用
        answer = asyncio.run(agent_run(data.question, history))
    # 原有模式（不改动）
    elif data.kb_id:
        answer = ask_with_rag(data.question, data.kb_id, history=history, summary=summary)
    elif history or summary:
        messages = []
        if summary:
            messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": data.question})
        answer = chat_completion(messages)
    else:
        answer = chat_completion([{"role": "user", "content": data.question}])

    _save_conversation(data, answer, current_user, db)
    _post_chat(session, data, answer, db)

    return ChatResponse(answer=answer, kb_id=data.kb_id)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: add agent mode to chat endpoint"
```

---

### Task 9: 修改 chat 路由 — 流式对话接口

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 在 chat_stream() 函数中增加 agent 模式分支**

将 `chat_stream()` 函数（第 167-212 行）改为：

```python
@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式对话接口（支持多轮上下文）"""

    def generate():
        session = None
        summary = None
        history = None

        if data.session_id:
            session, summary, history = _load_session_history(data.session_id, db)

        full_answer = ""

        if data.mode == "agent":
            # Agent 流式模式
            import asyncio
            from app.services.langchain_agent import run_agent_stream as agent_stream

            async def stream_agent():
                result = ""
                async for chunk in agent_stream(data.question, history):
                    result += chunk
                    yield chunk
                return result

            # 同步生成器中运行异步 Agent 流
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                agen = stream_agent()
                while True:
                    try:
                        chunk = loop.run_until_complete(agen.__anext__())
                        full_answer_holder[0] += chunk
                        yield f"data: {chunk}\n\n"
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        elif data.kb_id:
            from app.services.rag import ask_with_rag_stream
            for chunk in ask_with_rag_stream(data.question, data.kb_id, history=history, summary=summary):
                full_answer += chunk
                yield f"data: {chunk}\n\n"
        elif history or summary:
            from app.services.llm import chat_completion_stream as llm_stream
            messages = []
            if summary:
                messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": data.question})
            for chunk in llm_stream(messages):
                full_answer += chunk
                yield f"data: {chunk}\n\n"
        else:
            from app.services.llm import chat_completion_stream as llm_stream
            for chunk in llm_stream([{"role": "user", "content": data.question}]):
                full_answer += chunk
                yield f"data: {chunk}\n\n"

        yield "data: [DONE]\n\n"

        # 对于 agent 模式，full_answer 需要特殊处理
        actual_answer = full_answer_holder[0] if data.mode == "agent" else full_answer
        _save_conversation(data, actual_answer, current_user, db)
        _post_chat(session, data, actual_answer, db)

    # agent 模式需要的可变容器
    full_answer_holder = [""]

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**注意：** 上面的代码有一个问题 — 普通模式下 `full_answer` 是局部变量，在 agent 分支中用了 `full_answer_holder`，但普通分支还是用 `full_answer`。需要统一处理。实际实现时改用一个可变容器（如 `result = {"answer": ""}`）统一所有分支。

- [ ] **Step 2: 实际实现 — 统一用可变容器**

将整个 `chat_stream()` 函数替换为以下版本（解决变量作用域问题）：

```python
@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式对话接口（支持多轮上下文）"""
    # 用字典作为可变容器，在嵌套函数间共享状态
    state = {"answer": "", "session": None, "summary": None, "history": None}

    if data.session_id:
        state["session"], state["summary"], state["history"] = _load_session_history(data.session_id, db)

    def generate():
        if data.mode == "agent":
            # Agent 流式模式
            import asyncio
            from app.services.langchain_agent import run_agent_stream as agent_stream

            async def _collect_agent():
                async for chunk in agent_stream(data.question, state["history"]):
                    state["answer"] += chunk
                    yield f"data: {chunk}\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                agen = _collect_agent()
                while True:
                    try:
                        event = loop.run_until_complete(agen.__anext__())
                        yield event
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        elif data.kb_id:
            from app.services.rag import ask_with_rag_stream
            for chunk in ask_with_rag_stream(data.question, data.kb_id, history=state["history"], summary=state["summary"]):
                state["answer"] += chunk
                yield f"data: {chunk}\n\n"
        elif state["history"] or state["summary"]:
            from app.services.llm import chat_completion_stream as llm_stream
            messages = []
            if state["summary"]:
                messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{state['summary']}"})
            if state["history"]:
                messages.extend(state["history"])
            messages.append({"role": "user", "content": data.question})
            for chunk in llm_stream(messages):
                state["answer"] += chunk
                yield f"data: {chunk}\n\n"
        else:
            from app.services.llm import chat_completion_stream as llm_stream
            for chunk in llm_stream([{"role": "user", "content": data.question}]):
                state["answer"] += chunk
                yield f"data: {chunk}\n\n"

        yield "data: [DONE]\n\n"
        _save_conversation(data, state["answer"], current_user, db)
        _post_chat(state["session"], data, state["answer"], db)

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: add agent streaming mode to chat stream endpoint"
```

---

### Task 10: 端到端验证

- [ ] **Step 1: 启动后端服务**

Run: `cd F:/IntraAI/backend && python -m uvicorn app.main:app --reload --port 8000`
Expected: 服务正常启动，无 import 错误

- [ ] **Step 2: 测试普通模式未受影响**

Run: `curl -X POST http://localhost:8000/api/chat/ -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"question": "你好"}'`
Expected: 正常返回 AI 回答（走原有流程）

- [ ] **Step 3: 测试 Agent 模式（非流式）**

Run: `curl -X POST http://localhost:8000/api/chat/ -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"question": "今天有什么新闻？", "mode": "agent"}'`
Expected: Agent 调用 web_search 工具，返回搜索结果摘要

- [ ] **Step 4: 测试 Agent 模式（流式）**

Run: `curl -X POST http://localhost:8000/api/chat/stream -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"question": "帮我查一下数据库里有多少用户", "mode": "agent"}'`
Expected: SSE 流式返回，Agent 先调用 db_query，再生成回答

- [ ] **Step 5: 测试前端普通模式**

在浏览器中打开前端，正常使用聊天功能，确认不走 agent 模式的行为与之前完全一致。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: complete LangChain agent integration"
```
