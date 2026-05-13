# 多轮对话会话系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现多轮对话上下文维护，引入会话（Session）概念，支持 LLM 摘要压缩和自动标题生成。

**Architecture:** 新增 sessions 表管理会话，conversations 表关联 session_id，后端拼接历史上下文发给 LLM，超过 20 轮时压缩前 15 轮为摘要。前端改为左侧会话列表 + 右侧对话区的 ChatGPT 风格布局。

**Tech Stack:** Python/FastAPI, SQLAlchemy, Vue 3, Ant Design Vue, Pinia

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/models/session.py` | 新增 | Session ORM 模型 |
| `backend/app/models/__init__.py` | 修改 | 注册 Session 模型 |
| `backend/app/models/conversation.py` | 修改 | 添加 session_id 外键 |
| `backend/app/schemas/session.py` | 新增 | Session Pydantic 模型 |
| `backend/app/schemas/chat.py` | 修改 | ChatRequest 添加 session_id |
| `backend/app/api/sessions.py` | 新增 | Session CRUD 路由 |
| `backend/app/api/chat.py` | 修改 | 标题生成、摘要压缩调用 |
| `backend/app/services/llm.py` | 修改 | 添加 generate_title 和 generate_summary 函数 |
| `backend/app/services/rag.py` | 修改 | 支持拼接历史上下文 |
| `backend/app/main.py` | 修改 | 注册 sessions 路由 |
| `frontend/src/api/session.js` | 新增 | Session API 封装 |
| `frontend/src/api/chat.js` | 修改 | sendChat 支持 session_id |
| `frontend/src/views/ChatView.vue` | 重构 | 左侧会话栏 + 右侧对话区 |

---

### Task 1: 创建 Session 数据模型

**Files:**
- Create: `backend/app/models/session.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 Session 模型文件**

```python
# backend/app/models/session.py
"""
会话数据模型

定义 Session（会话）表结构。
每个会话包含多轮对话记录，支持摘要压缩以控制 LLM 上下文 token 消耗。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Session(Base):
    """会话表 — 存储用户的对话会话"""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, default="新对话")
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: 在 models/__init__.py 中注册 Session**

在文件末尾添加导入：

```python
from app.models.session import Session
```

完整文件内容：

```python
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.usage_log import UsageLog
from app.models.session import Session
```

- [ ] **Step 3: 验证模型加载**

运行以下命令检查模型是否能正确导入：
```bash
cd backend && python -c "from app.models.session import Session; print('OK')"
```
Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/session.py backend/app/models/__init__.py
git commit -m "feat: add Session model for multi-turn conversation"
```

---

### Task 2: 给 Conversation 模型添加 session_id

**Files:**
- Modify: `backend/app/models/conversation.py`

- [ ] **Step 1: 添加 session_id 字段**

在 `Conversation` 类中，`kb_id` 字段之后添加：

```python
# 新增：关联会话 ID，nullable=True 兼容旧数据（旧对话没有 session_id）
session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
```

完整字段区域应为：

```python
id = Column(Integer, primary_key=True, autoincrement=True)
user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
kb_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True)
session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)  # 新增
question = Column(Text, nullable=False)
answer = Column(Text, nullable=False)
created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/conversation.py
git commit -m "feat: add session_id to Conversation model"
```

---

### Task 3: 创建 Session Pydantic Schema

**Files:**
- Create: `backend/app/schemas/session.py`

- [ ] **Step 1: 创建 schema 文件**

```python
# backend/app/schemas/session.py
"""会话相关 Pydantic 模型"""

from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    """创建会话的请求体（无字段，直接创建空会话）"""
    pass


class SessionOut(BaseModel):
    """会话的响应体"""
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(BaseModel):
    """会话详情（含对话记录列表）"""
    id: int
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    conversations: list["ConversationItem"] = []

    class Config:
        from_attributes = True


class ConversationItem(BaseModel):
    """单条对话记录（用于会话详情中的对话列表）"""
    id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/session.py
git commit -m "feat: add Session Pydantic schemas"
```

---

### Task 4: 修改 ChatRequest 支持 session_id

**Files:**
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: 给 ChatRequest 添加 session_id 字段**

```python
class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None  # 新增：可选的会话 ID
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "feat: add session_id to ChatRequest schema"
```

---

### Task 5: 创建 Session API 路由

**Files:**
- Create: `backend/app/api/sessions.py`

- [ ] **Step 1: 创建 sessions 路由文件**

```python
# backend/app/api/sessions.py
"""会话管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.session import Session
from app.models.conversation import Conversation
from app.schemas.session import SessionOut, SessionDetail, ConversationItem

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.post("/", response_model=SessionOut)
def create_session(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建会话"""
    session = Session(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户所有会话（按更新时间倒序）"""
    return (
        db.query(Session)
        .filter(Session.user_id == current_user.id)
        .order_by(desc(Session.updated_at))
        .all()
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情（含对话记录）"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    # 手动构造响应，因为 SessionDetail 需要嵌套 conversations
    return SessionDetail(
        id=session.id,
        title=session.title,
        summary=session.summary,
        created_at=session.created_at,
        updated_at=session.updated_at,
        conversations=[
            ConversationItem(
                id=c.id,
                question=c.question,
                answer=c.answer,
                created_at=c.created_at,
            )
            for c in conversations
        ],
    )


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: DbSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话及其下所有对话记录"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")

    # 先删除该会话下的所有对话记录
    db.query(Conversation).filter(Conversation.session_id == session_id).delete()
    # 再删除会话本身
    db.delete(session)
    db.commit()
    return {"message": "已删除"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/sessions.py
git commit -m "feat: add sessions CRUD API routes"
```

---

### Task 6: 在 main.py 注册 sessions 路由

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 添加 sessions 路由导入和注册**

在导入区域添加：
```python
from app.api.sessions import router as sessions_router
```

在 `app.include_router(admin_router)` 之后添加：
```python
# 注册会话管理路由（/api/sessions/）
app.include_router(sessions_router)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register sessions router in main.py"
```

---

### Task 7: 给 LLM 服务添加标题生成和摘要压缩函数

**Files:**
- Modify: `backend/app/services/llm.py`

- [ ] **Step 1: 添加 generate_title 函数**

在 `chat_completion_stream` 函数之后添加：

```python
def generate_title(question: str, answer: str) -> str:
    """
    根据第一轮对话生成会话标题。

    参数：
        question: 用户的问题
        answer: AI 的回答

    返回：
        不超过20个字的标题
    """
    prompt = (
        "请用不超过20个字概括以下对话的主题，只输出标题，不要加引号：\n"
        f"用户问：{question}\n"
        f"AI答：{answer}"
    )
    title = chat_completion([{"role": "user", "content": prompt}])
    # 去除可能的引号和多余空白
    return title.strip().strip('"').strip("'").strip("「」").strip("""""")[:50]


def generate_summary(conversations: list[dict]) -> str:
    """
    对多轮对话生成摘要。

    参数：
        conversations: 对话列表，每项包含 role 和 content

    返回：
        摘要文本
    """
    history_text = ""
    for conv in conversations:
        role_label = "用户" if conv["role"] == "user" else "AI"
        history_text += f"{role_label}：{conv['content']}\n\n"

    prompt = (
        "请用简洁的语言概括以下对话的主要内容和结论，控制在200字以内：\n\n"
        f"{history_text}"
    )
    return chat_completion([{"role": "user", "content": prompt}])
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/llm.py
git commit -m "feat: add generate_title and generate_summary to LLM service"
```

---

### Task 8: 修改 RAG 服务支持历史上下文

**Files:**
- Modify: `backend/app/services/rag.py`

- [ ] **Step 1: 给 ask_with_rag 添加 history 和 summary 参数**

修改 `ask_with_rag` 函数签名为：

```python
def ask_with_rag(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
) -> str:
```

修改 `ask_with_rag` 中 messages 构建逻辑（替换原来的 messages 构建部分）：

```python
    # 步骤 4：构造消息列表
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    # 如果有摘要，作为额外的系统消息插入
    if summary:
        messages.append({
            "role": "system",
            "content": f"以下是对之前对话的摘要：\n{summary}",
        })

    # 如果有历史对话，插入到当前问题之前
    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    # 最后追加当前问题
    messages.append({"role": "user", "content": question})

    return chat_completion(messages)
```

- [ ] **Step 2: 给 ask_with_rag_stream 添加同样的参数**

修改 `ask_with_rag_stream` 函数签名为：

```python
def ask_with_rag_stream(
    question: str,
    kb_id: int,
    history: list[dict] | None = None,
    summary: str | None = None,
):
```

修改 `ask_with_rag_stream` 中 messages 构建逻辑（替换原来的 messages 构建部分）：

```python
    # 步骤 4：构造消息
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]

    if summary:
        messages.append({
            "role": "system",
            "content": f"以下是对之前对话的摘要：\n{summary}",
        })

    if history:
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

    messages.append({"role": "user", "content": question})

    yield from chat_completion_stream(messages)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/rag.py
git commit -m "feat: add history and summary support to RAG service"
```

---

### Task 9: 修改 Chat API 支持 session_id、标题生成和摘要压缩

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 添加新的导入**

在文件顶部添加：

```python
from sqlalchemy import func as sql_func, asc
from app.models.session import Session
from app.services.llm import generate_title, generate_summary
```

- [ ] **Step 2: 重构 chat 函数**

将 `chat` 函数整体替换为：

```python
@router.post("/", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通对话接口（支持多轮上下文）"""
    history = None
    summary = None
    session = None

    # 如果指定了 session_id，加载历史上下文
    if data.session_id:
        session = db.query(Session).filter(
            Session.id == data.session_id,
            Session.user_id == current_user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 获取该会话的摘要（如果有）
        summary = session.summary

        # 获取最近 5 轮对话作为历史上下文
        recent_convs = (
            db.query(Conversation)
            .filter(Conversation.session_id == data.session_id)
            .order_by(Conversation.created_at.desc())
            .limit(5)
            .all()
        )
        # 按时间正序排列（因为 desc 取出是倒序的）
        recent_convs = list(reversed(recent_convs))
        if recent_convs:
            history = []
            for conv in recent_convs:
                history.append({"role": "user", "content": conv.question})
                history.append({"role": "assistant", "content": conv.answer})

    # 执行对话
    if data.kb_id:
        answer = ask_with_rag(data.question, data.kb_id, history=history, summary=summary)
    elif history or summary:
        # 有上下文但无知识库：直接拼历史问 LLM
        messages = []
        if summary:
            messages.append({"role": "system", "content": f"以下是对之前对话的摘要：\n{summary}"})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": data.question})
        answer = chat_completion(messages)
    else:
        # 无上下文无知识库：当前逻辑
        answer = chat_completion([{"role": "user", "content": data.question}])

    # 保存对话记录
    conv = Conversation(
        user_id=current_user.id,
        kb_id=data.kb_id,
        session_id=data.session_id,
        question=data.question,
        answer=answer,
    )
    db.add(conv)

    # 记录用量日志
    log = UsageLog(user_id=current_user.id, action="chat")
    db.add(log)

    # 如果有关联会话，更新会话的 updated_at
    if session:
        session.updated_at = sql_func.now()

    db.commit()

    # 标题生成：如果是会话的第一条消息且标题还是"新对话"
    if session and session.title == "新对话":
        title = generate_title(data.question, answer)
        session.title = title
        db.commit()

    # 摘要压缩：检查对话数量是否达到 20
    if session:
        _maybe_compress(session.id, db)

    return ChatResponse(answer=answer, kb_id=data.kb_id)
```

- [ ] **Step 3: 重构 chat_stream 函数**

将 `chat_stream` 函数整体替换为：

```python
@router.post("/stream")
def chat_stream(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式对话接口（支持多轮上下文）"""

    def generate():
        history = None
        summary = None
        session = None

        if data.session_id:
            session = db.query(Session).filter(
                Session.id == data.session_id,
                Session.user_id == current_user.id,
            ).first()
            if session:
                summary = session.summary
                recent_convs = (
                    db.query(Conversation)
                    .filter(Conversation.session_id == data.session_id)
                    .order_by(Conversation.created_at.desc())
                    .limit(5)
                    .all()
                )
                recent_convs = list(reversed(recent_convs))
                if recent_convs:
                    history = []
                    for conv in recent_convs:
                        history.append({"role": "user", "content": conv.question})
                        history.append({"role": "assistant", "content": conv.answer})

        full_answer = ""

        if data.kb_id:
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

        # 保存对话记录
        conv = Conversation(
            user_id=current_user.id,
            kb_id=data.kb_id,
            session_id=data.session_id,
            question=data.question,
            answer=full_answer,
        )
        db.add(conv)

        log = UsageLog(user_id=current_user.id, action="chat")
        db.add(log)

        if session:
            session.updated_at = sql_func.now()

        db.commit()

        # 标题生成
        if session and session.title == "新对话":
            title = generate_title(data.question, full_answer)
            session.title = title
            db.commit()

        # 摘要压缩
        if session:
            _maybe_compress(session.id, db)

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 4: 添加摘要压缩辅助函数**

在 `chat_stream` 函数之后添加：

```python
def _maybe_compress(session_id: int, db: Session):
    """检查会话对话数量，超过 20 轮时触发摘要压缩"""
    conv_count = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .count()
    )

    if conv_count < 20:
        return

    # 取前 15 轮对话
    old_convs = (
        db.query(Conversation)
        .filter(Conversation.session_id == session_id)
        .order_by(asc(Conversation.created_at))
        .limit(15)
        .all()
    )

    # 构造对话列表用于生成摘要
    conversations = []
    for conv in old_convs:
        conversations.append({"role": "user", "content": conv.question})
        conversations.append({"role": "assistant", "content": conv.answer})

    # 调用 LLM 生成摘要
    new_summary = generate_summary(conversations)

    # 获取会话，拼接已有摘要
    session = db.query(Session).filter(Session.id == session_id).first()
    if session and session.summary:
        # 如果已有摘要，将新旧摘要合并
        combined = f"{session.summary}\n\n---\n\n{new_summary}"
    else:
        combined = new_summary

    # 更新会话摘要
    session.summary = combined

    # 删除这 15 轮对话记录
    for conv in old_convs:
        db.delete(conv)

    db.commit()
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: add session support to chat API with title generation and summary compression"
```

---

### Task 10: 创建前端 Session API 模块

**Files:**
- Create: `frontend/src/api/session.js`

- [ ] **Step 1: 创建 API 模块文件**

```javascript
// frontend/src/api/session.js
/**
 * 会话 API 模块
 *
 * 封装会话管理相关的后端接口请求。
 */
import api from './index'

/**
 * 创建新会话
 * @returns {Promise} 返回新创建的会话对象
 */
export function createSession() {
  return api.post('/api/sessions/')
}

/**
 * 获取当前用户所有会话
 * @returns {Promise} 返回会话列表（按更新时间倒序）
 */
export function listSessions() {
  return api.get('/api/sessions/')
}

/**
 * 获取会话详情（含对话记录）
 * @param {number} id - 会话 ID
 * @returns {Promise} 返回会话详情对象
 */
export function getSession(id) {
  return api.get(`/api/sessions/${id}`)
}

/**
 * 删除会话及其下所有对话记录
 * @param {number} id - 要删除的会话 ID
 * @returns {Promise}
 */
export function deleteSession(id) {
  return api.delete(`/api/sessions/${id}`)
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/session.js
git commit -m "feat: add session API module for frontend"
```

---

### Task 11: 修改 sendChat 支持 session_id

**Files:**
- Modify: `frontend/src/api/chat.js`

- [ ] **Step 1: 更新 sendChat 注释**

```javascript
/**
 * 发送对话请求
 *
 * @param {Object} data - 请求数据
 * @param {string} data.question - 用户提出的问题
 * @param {number|null} data.kb_id - 可选的知识库 ID
 * @param {number|null} data.session_id - 可选的会话 ID，用于多轮对话上下文
 * @returns {Promise} 返回包含 AI 回答的响应对象
 */
export function sendChat(data) {
  return api.post('/api/chat/', data)
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/chat.js
git commit -m "feat: update sendChat to support session_id"
```

---

### Task 12: 重构 ChatView.vue 为左侧会话栏 + 右侧对话区

**Files:**
- Modify: `frontend/src/views/ChatView.vue`

- [ ] **Step 1: 替换整个 ChatView.vue**

```vue
<!--
  ChatView 对话页面

  布局：左侧会话列表 + 右侧对话区（ChatGPT 风格）
-->
<template>
  <a-layout style="height: 100vh">
    <!-- 顶部导航栏 -->
    <a-layout-header class="header">
      <div class="logo">IntraAI</div>
      <a-menu theme="dark" mode="horizontal" :selected-keys="['chat']">
        <a-menu-item key="chat">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin" v-if="authStore.user?.is_admin" @click="$router.push('/admin')">管理</a-menu-item>
      </a-menu>
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>

    <a-layout>
      <!-- 左侧会话栏 -->
      <a-layout-sider width="260" class="sider">
        <div class="sider-header">
          <a-button type="primary" block @click="handleNewSession">
            + 新建对话
          </a-button>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: currentSessionId === s.id }]"
            @click="handleSelectSession(s.id)"
          >
            <span class="session-title">{{ s.title }}</span>
            <a-button
              type="text"
              size="small"
              class="delete-btn"
              @click.stop="handleDeleteSession(s.id)"
            >
              X
            </a-button>
          </div>
          <a-empty v-if="sessions.length === 0" description="暂无对话" :image-style="{ height: '40px' }" />
        </div>
      </a-layout-sider>

      <!-- 右侧对话区 -->
      <a-layout-content class="chat-content">
        <div class="chat-area">
          <div class="messages" ref="messagesRef">
            <a-empty v-if="messages.length === 0" description="选择知识库后开始提问" />
            <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
          </div>

          <div class="input-area">
            <a-select
              v-model:value="selectedKb"
              placeholder="选择知识库（可选）"
              style="width: 200px; margin-bottom: 8px"
              :options="kbOptions"
              allow-clear
            />
            <div class="input-row">
              <a-textarea
                v-model:value="question"
                placeholder="输入问题..."
                :auto-size="{ minRows: 1, maxRows: 4 }"
                @keydown.enter.exact="handleSend"
              />
              <a-button type="primary" :loading="loading" @click="handleSend">发送</a-button>
            </div>
          </div>
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases } from '../api/knowledge'
import { sendChat } from '../api/chat'
import { createSession, listSessions, getSession, deleteSession } from '../api/session'
import ChatMessage from '../components/ChatMessage.vue'

const router = useRouter()
const authStore = useAuthStore()

const messages = ref([])
const question = ref('')
const loading = ref(false)
const selectedKb = ref(null)
const kbOptions = ref([])
const messagesRef = ref(null)

// 会话相关状态
const sessions = ref([])
const currentSessionId = ref(null)

/**
 * 获取会话列表
 */
async function fetchSessions() {
  const res = await listSessions()
  sessions.value = res.data
}

/**
 * 获取知识库列表
 */
async function fetchKbs() {
  const res = await listKnowledgeBases()
  kbOptions.value = res.data.map(kb => ({ label: kb.name, value: kb.id }))
}

/**
 * 新建对话
 */
async function handleNewSession() {
  const res = await createSession()
  const newSession = res.data
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  messages.value = []
}

/**
 * 选择会话：加载该会话的对话记录
 */
async function handleSelectSession(sessionId) {
  currentSessionId.value = sessionId
  const res = await getSession(sessionId)
  messages.value = res.data.conversations.flatMap(conv => [
    { role: 'user', content: conv.question },
    { role: 'assistant', content: conv.answer },
  ])
  await nextTick()
  scrollToBottom()
}

/**
 * 删除会话
 */
function handleDeleteSession(sessionId) {
  Modal.confirm({
    title: '确认删除',
    content: '删除后该对话将无法恢复，确认删除？',
    onOk: async () => {
      await deleteSession(sessionId)
      sessions.value = sessions.value.filter(s => s.id !== sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        messages.value = []
      }
      message.success('已删除')
    },
  })
}

/**
 * 发送消息
 */
async function handleSend() {
  if (!question.value.trim() || loading.value) return

  const q = question.value.trim()
  question.value = ''

  messages.value.push({ role: 'user', content: q })
  loading.value = true

  await nextTick()
  scrollToBottom()

  try {
    const res = await sendChat({
      question: q,
      kb_id: selectedKb.value,
      session_id: currentSessionId.value,
    })
    messages.value.push({ role: 'assistant', content: res.data.answer })

    // 刷新会话列表（标题可能已更新）
    fetchSessions()
  } catch {
    message.error('发送失败')
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
  fetchSessions()
})
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
}
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
}
/* 左侧会话栏 */
.sider {
  background: #fff;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
}
.sider-header {
  padding: 12px;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.session-item:hover {
  background: #f5f5f5;
}
.session-item.active {
  background: #e6f4ff;
  color: #1677ff;
}
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.delete-btn {
  opacity: 0;
  color: #999;
  font-size: 12px;
  padding: 0 4px;
}
.session-item:hover .delete-btn {
  opacity: 1;
}
/* 右侧对话区 */
.chat-content {
  display: flex;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}
.chat-area {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.input-area {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}
.input-row {
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ChatView.vue
git commit -m "feat: refactor ChatView with session sidebar layout"
```

---

### Task 13: 端到端验证

- [ ] **Step 1: 启动后端验证 API**

```bash
cd backend && uvicorn app.main:app --reload
```

检查：
1. 访问 `http://localhost:8000/docs`，确认 Sessions API 出现在 Swagger 文档中
2. 用 Swagger 测试 `POST /api/sessions/` 创建会话
3. 用 Swagger 测试 `GET /api/sessions/` 列出会话
4. 用 Swagger 测试 `POST /api/chat/` 带 session_id 发送对话
5. 用 Swagger 测试 `GET /api/sessions/{id}` 确认对话记录被关联

- [ ] **Step 2: 启动前端验证 UI**

```bash
cd frontend && npm run dev
```

检查：
1. 左侧会话栏正常显示
2. 点击"新建对话"创建新会话并出现在列表中
3. 发送消息后标题被自动更新
4. 点击历史会话能加载对话记录
5. 删除会话功能正常
6. 多轮对话上下文正常（第二轮能理解第一轮的语境）

- [ ] **Step 3: 最终提交**

确认所有改动正常后，如有遗漏的修复一并提交。

```bash
git add -A && git commit -m "fix: minor fixes after end-to-end verification"
```
