# 多轮对话会话系统设计

## 概述

为 IntraAI 添加多轮对话上下文维护能力。引入"会话（Session）"概念，每个会话包含多轮对话记录，支持 LLM 摘要压缩以控制 token 消耗。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 会话创建方式 | 手动（"新建对话"按钮） | 用户主动控制对话边界 |
| 摘要压缩触发 | 超过 20 轮时触发 | 保留足够的原始上下文，token 消耗可控 |
| 标题生成 | LLM 根据第一轮对话自动生成 | 无需用户手动输入，标题语义清晰 |
| 前端布局 | 左侧会话列表 + 右侧对话区 | ChatGPT 风格，多会话管理直观 |

## 数据库变更

### 新增 `sessions` 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, auto_increment | 主键 |
| user_id | INT | FK→users, NOT NULL | 会话所属用户 |
| title | VARCHAR(255) | NOT NULL, default "新对话" | LLM 自动生成的标题 |
| summary | TEXT | NULLABLE | 压缩后的早期对话摘要 |
| created_at | DATETIME | server_default=now() | 创建时间 |
| updated_at | DATETIME | server_default=now(), on_update=now() | 最后活跃时间 |

### `conversations` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| session_id | INT | FK→sessions, NULLABLE | 关联的会话（NULL 表示旧数据或无会话对话） |

## 后端变更

### 新增 API 路由 `/api/sessions/`

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sessions/` | POST | 新建会话，返回 session（title 默认为"新对话"） |
| `/api/sessions/` | GET | 获取当前用户所有会话，按 updated_at 倒序 |
| `/api/sessions/{id}` | GET | 获取会话详情（含该会话下的对话记录） |
| `/api/sessions/{id}` | DELETE | 删除会话及其下所有对话记录和 ChromaDB 数据（如果关联了知识库） |

### `POST /api/chat/` 改动

请求体新增字段：
```json
{
  "question": "公司有多少天年假？",
  "kb_id": 1,
  "session_id": 5
}
```

**拼接 messages 的逻辑**（当 session_id 不为空时）：

```
messages = [
    system: SYSTEM_PROMPT（含 RAG 检索到的上下文）,
    system: "以下是对之前对话的摘要：{summary}",    # 仅在 summary 存在时添加
    ...历史对话（最近 5 轮）,
    user: 当前问题
]
```

如果 session_id 为空，走当前逻辑（无上下文，单轮 RAG）。

### 摘要压缩机制

触发条件：session 下的对话记录数量 ≥ 20

压缩流程：
1. 取前 15 轮对话记录
2. 调用 LLM，prompt：`"请用简洁的语言概括以下对话的主要内容和结论：{前15轮对话}"`
3. 将生成的摘要存入 `sessions.summary`
4. 删除这 15 轮 `conversations` 记录
5. 保留后 5 轮原始记录

效果：下次拼 messages 时 = summary + 最近 5 轮 + 当前问题，控制 token 量。

### 标题生成机制

触发时机：用户在该会话中发送第一条消息并获得回答后

生成方式：调用 LLM，prompt：
```
"请用不超过20个字概括以下对话的主题，只输出标题，不要加引号：
用户问：{question}
AI答：{answer}"
```

将生成的标题更新到 `sessions.title`。

## 前端变更

### 布局重构（ChatView.vue）

```
┌──────────────┬─────────────────────────────────────┐
│              │  IntraAI  对话  知识库  管理  [退出]   │
├──────────────┼─────────────────────────────────────┤
│ [+] 新建对话  │                                      │
│              │                                      │
│ ● 会议制度咨询│ ← 当前选中（高亮）                     │
│   年假政策讨论│                                      │
│   考勤问题汇总│       消息列表                         │
│   ...        │                                      │
│              │  ┌────────────────────────┐           │
│  左侧会话栏   │  │ [知识库] [输入框...] [发送]│           │
│  (宽度约240px)│  └────────────────────────┘           │
└──────────────┴─────────────────────────────────────┘
```

### 交互流程

1. **页面加载**：调 `GET /api/sessions/` 获取会话列表渲染到侧边栏
2. **点击"新建对话"**：调 `POST /api/sessions/` → 新会话出现在列表顶部并选中 → 右侧清空
3. **点击某会话**：切换选中 → 调 `GET /api/sessions/{id}` 加载对话记录到右侧
4. **发送消息**：`sendChat({ question, kb_id, session_id })` 带上当前选中的 session_id
5. **标题更新**：收到第一条消息的回复后，后端生成标题，前端刷新该会话标题
6. **删除会话**：hover 显示删除图标 → 确认后调 DELETE → 从列表移除，如果删除的是当前会话则切换到空状态

### 新增 API 模块 `frontend/src/api/session.js`

```javascript
export function createSession()           // POST /api/sessions/
export function listSessions()            // GET  /api/sessions/
export function getSession(id)            // GET  /api/sessions/{id}
export function deleteSession(id)         // DELETE /api/sessions/{id}
```

## 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/session.py` | 新增 | Session ORM 模型 |
| `backend/app/models/conversation.py` | 修改 | 添加 session_id 字段 |
| `backend/app/schemas/session.py` | 新增 | Session 相关 Pydantic 模型 |
| `backend/app/schemas/chat.py` | 修改 | ChatRequest 添加 session_id |
| `backend/app/api/sessions.py` | 新增 | Session CRUD 路由 |
| `backend/app/api/chat.py` | 修改 | 支持 session_id、摘要压缩、标题生成 |
| `backend/app/services/rag.py` | 修改 | 支持拼接历史上下文和摘要 |
| `backend/app/main.py` | 修改 | 注册 sessions 路由 |
| `frontend/src/api/session.js` | 新增 | Session API 封装 |
| `frontend/src/views/ChatView.vue` | 重构 | 左侧会话栏 + 右侧对话区布局 |
| `frontend/src/components/ChatMessage.vue` | 不变 | 无需修改 |
