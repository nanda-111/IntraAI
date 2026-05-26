# DeepSeek 风格聊天界面 + 流式思考过程

## 背景

当前聊天界面是基础的 ChatGPT 风格：蓝/灰气泡、非流式请求、无思考过程展示。需要改造为 DeepSeek 风格：深色侧边栏、扁平消息样式、可折叠思考过程面板、流式输出可切换。

## 决策记录

- MiMo API 支持 `reasoning_content` 字段，直接接入
- 流式/非流式做成用户可切换的开关
- 视觉：深色侧边栏(A) + 折叠思考面板(B) + 用户纯文本靠右/ AI 左头像无气泡(C) + 固定底部输入含模型选择(D)
- 思考面板：流式时展开，完成后自动收起为"已思考 X 秒"
- 模型下拉框：硬编码几个 MiMo 选项
- 其他页面（LoginView、KnowledgeView、AdminView）顶部导航也同步改为深色侧边栏

## 改动文件清单

### 后端（2 个文件）

#### 1. `backend/app/services/llm.py` — 透传 reasoning_content

当前 `chat_completion_stream` 只 yield `delta.content`。需要同时 yield `delta.reasoning_content`。

改法：yield 一个 dict 而非纯字符串，区分类型：

```python
# 之前
if chunk.choices[0].delta.content:
    yield chunk.choices[0].delta.content

# 之后
delta = chunk.choices[0].delta
if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
    yield {"type": "reasoning", "content": delta.reasoning_content}
elif delta.content:
    yield {"type": "answer", "content": delta.content}
```

`chat_completion`（非流式）同样需要返回 reasoning_content。从 response 中提取 `response.choices[0].message.reasoning_content`，返回 tuple `(reasoning, answer)`。

#### 2. `backend/app/api/chat.py` — SSE 格式区分 reasoning/answer

流式端点 `chat_stream` 的 `generate()` 函数中，对 yield 的 dict 做 SSE 序列化：

```python
if isinstance(chunk, dict):
    yield f"data: {json.dumps(chunk)}\n\n"  # {"type":"reasoning","content":"..."} 或 {"type":"answer","content":"..."}
else:
    yield f"data: {chunk}\n\n"  # 兼容旧格式
```

非流式端点 `chat` 需要适配 `chat_completion` 返回 tuple 的变化：提取 answer 字段返回，reasoning 不返回（非流式不需要）。

新增 schema 字段：`ChatRequest` 增加 `stream: bool = False`，让前端可以控制是否走流式。

#### 3. `backend/app/schemas/chat.py` — 新增 stream 字段

```python
class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None
    mode: Literal["normal", "agent"] = "normal"
    stream: bool = False
```

### 前端（5 个文件）

#### 1. `frontend/src/api/chat.js` — 新增流式请求函数

```javascript
// 新增：SSE 流式对话，返回 AsyncGenerator
export async function* sendChatStream(data) {
  const token = localStorage.getItem('token')
  const baseURL = import.meta.env.PROD ? '' : 'http://localhost:8000'
  const res = await fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') return
        if (data === '[ERROR]') throw new Error('Stream error')
        try {
          yield JSON.parse(data) // {type: "reasoning"|"answer", content: "..."}
        } catch {
          yield { type: 'answer', content: data } // 兼容旧格式
        }
      }
    }
  }
}
```

#### 2. `frontend/src/components/ChatMessage.vue` — 重写消息组件

**用户消息**：去掉气泡背景，纯文本靠右对齐，无头像。

**AI 消息**：左侧圆形头像（DeepSeek 蓝色 `#4D6BFE`），无气泡背景，内容区域全宽。

**思考过程面板**（新增）：
- 仅当 `message.reasoning` 非空时渲染
- 使用 `<details>` 或自定义折叠组件
- 折叠态：显示 "已思考 X 秒" + 展开箭头
- 展开态：显示完整的思考内容，灰色斜体，左侧竖线装饰
- 流式中（`message.streaming === true`）：面板展开，内容逐字追加
- 流式结束（`message.streaming === false`）：0.5s 后自动收起

**Props 扩展**：
```javascript
message: {
  role: 'user' | 'assistant',
  content: string,
  reasoning: string,        // 思考过程文本
  reasoning_time: number,   // 思考耗时（秒）
  streaming: boolean,       // 是否正在流式输出
}
```

#### 3. `frontend/src/views/ChatView.vue` — 重构主布局

**布局改动**：
- 去掉 `<a-layout-header>` 顶部深色导航栏
- 左侧 `<a-layout-sider>` 改为深色背景（`#1a1a2e`），包含：
  - Logo "IntraAI"（白色）
  - "新建对话" 按钮
  - 会话列表
  - 底部导航链接（对话、知识库、管理）
  - 退出按钮
- 右侧内容区去掉 max-width 限制，改为全宽

**输入区改动**：
- 底部固定定位（`position: sticky; bottom: 0`）
- 上方增加一行工具栏：
  - 模型选择下拉框（硬编码：MiMo v2 Pro, MiMo v2 Lite 等）
  - 流式/非流式切换开关（`a-switch`）
  - 知识库选择（保留现有）
- 输入框增大，圆角风格

**handleSend 逻辑改动**：
```javascript
async function handleSend() {
  if (!question.value.trim() || loading.value) return
  const q = question.value.trim()
  question.value = ''
  messages.value.push({ role: 'user', content: q })
  loading.value = true

  if (useStream.value) {
    // 流式模式
    messages.value.push({
      role: 'assistant', content: '', reasoning: '',
      reasoning_time: 0, streaming: true
    })
    const msg = messages.value[messages.value.length - 1]
    const startTime = Date.now()
    let reasoningStartTime = null

    try {
      for await (const chunk of sendChatStream({
        question: q, kb_id: selectedKb.value,
        session_id: currentSessionId.value, mode: selectedMode.value
      })) {
        if (chunk.type === 'reasoning') {
          if (!reasoningStartTime) reasoningStartTime = Date.now()
          msg.reasoning += chunk.content
        } else if (chunk.type === 'answer') {
          if (reasoningStartTime && !msg.reasoning_time) {
            msg.reasoning_time = Math.round((Date.now() - reasoningStartTime) / 1000)
          }
          msg.content += chunk.content
        }
        scrollToBottom()
      }
    } catch { message.error('发送失败') }
    finally {
      msg.streaming = false
      loading.value = false
      fetchSessions()
    }
  } else {
    // 非流式模式（保持现有逻辑）
    try {
      const res = await sendChat({ question: q, kb_id: selectedKb.value, session_id: currentSessionId.value })
      messages.value.push({ role: 'assistant', content: res.data.answer })
      fetchSessions()
    } catch { message.error('发送失败') }
    finally { loading.value = false; scrollToBottom() }
  }
}
```

**新增状态**：
- `useStream` (ref, 默认 true) — 流式开关
- `selectedModel` (ref) — 当前选中模型
- `selectedMode` (ref, 'normal') — 对话模式

#### 4. `frontend/src/views/LoginView.vue` — 色调微调

登录页背景改为与深色侧边栏一致的色系：
- 背景：`#1a1a2e`（深色）
- 卡片：白色，圆角加大（`border-radius: 12px`）
- 主色调按钮：`#4D6BFE`（DeepSeek 蓝）
- 链接色：`#4D6BFE`

#### 5. `frontend/src/style.css` — 全局样式重置

清理掉当前 Vite 模板的默认样式，改为适配聊天应用的极简 reset：
- body 背景：`#f7f7f8`（浅灰，DeepSeek 主区域色）
- 字体：系统字体栈
- 去掉 #app 的 max-width 和 border 约束

### 后端 Agent 流式适配

#### `backend/app/services/langchain_agent.py`

Agent 流式函数 `run_agent_stream` 同样需要 yield dict 格式，与 `chat_completion_stream` 保持一致。如果 Agent 不涉及 reasoning_content，直接 yield `{"type": "answer", "content": chunk}`。

## 数据流

```
用户点击发送
  → ChatView.handleSend()
  → sendChatStream({ question, kb_id, session_id, mode })
  → fetch POST /api/chat/stream (SSE)
  → 后端 chat_stream() → chat_completion_stream(messages)
  → MiMo API (stream=True)
  → chunk: { delta: { reasoning_content: "..." } }  → yield {"type":"reasoning","content":"..."}
  → chunk: { delta: { content: "..." } }             → yield {"type":"answer","content":"..."}
  → SSE: data: {"type":"reasoning","content":"..."}\n\n
  → 前端 ReadableStream 解析
  → msg.reasoning += ...  或  msg.content += ...
  → Vue 响应式更新 → ChatMessage 重新渲染
  → 收到 [DONE] → msg.streaming = false → 思考面板自动收起
```

## 思考面板 UI 规格

```
┌─────────────────────────────────────────────────┐
│ ▸ 已思考 3 秒                          [折叠态]  │
├─────────────────────────────────────────────────┤
│ ▾ 已思考 3 秒                          [展开态]  │
│ ┌─────────────────────────────────────────────┐ │
│ │ 思考过程文本...                              │ │
│ │ 逐字显示，灰色斜体                           │ │
│ │ 左侧 2px 竖线装饰 (#4D6BFE 蓝色)            │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## 测试计划

### 后端
1. 单元测试：`chat_completion_stream` yield dict 格式正确
2. 集成测试：`/api/chat/stream` SSE 响应包含 reasoning 和 answer 类型
3. 非流式接口仍然正常工作（向后兼容）

### 前端
1. 组件测试：ChatMessage 渲染思考面板（有/无 reasoning_content）
2. 组件测试：流式模式下 content 逐字更新
3. E2E：发送消息 → 看到思考过程 → 看到回答 → 面板自动收起
4. E2E：切换流式/非流式开关，两种模式都能正常工作

## 实施顺序

1. 后端 `llm.py` — yield dict 格式，透传 reasoning_content
2. 后端 `chat.py` — SSE 序列化 + schema 新增 stream 字段
3. 前端 `chat.js` — 新增 sendChatStream 函数
4. 前端 `ChatMessage.vue` — 重写消息样式 + 思考面板
5. 前端 `ChatView.vue` — 深色侧边栏 + 流式逻辑 + 模型选择
6. 前端 `LoginView.vue` — 色调微调
7. 前端 `style.css` — 全局样式调整
8. 集成测试验证完整流程
