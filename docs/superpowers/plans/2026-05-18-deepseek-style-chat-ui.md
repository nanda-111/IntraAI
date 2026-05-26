# DeepSeek 风格聊天界面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 IntraAI 聊天界面从基础 ChatGPT 风格改造为 DeepSeek 风格，支持流式思考过程展示。

**Architecture:** 后端 LLM 服务 yield dict 区分 reasoning/answer 类型 → SSE 透传 → 前端 fetch+ReadableStream 解析 → Vue 响应式逐字渲染 + 思考折叠面板。

**Tech Stack:** FastAPI, SSE, Vue 3, Ant Design Vue 4, markdown-it, Pinia

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/services/llm.py` | Modify | yield dict 格式区分 reasoning/answer，非流式返回 tuple |
| `backend/app/api/chat.py` | Modify | SSE 序列化 dict，适配 chat_completion 返回值变化 |
| `backend/app/schemas/chat.py` | Modify | 新增 stream 字段 |
| `backend/app/services/langchain_agent.py` | Modify | run_agent_stream yield dict 格式 |
| `backend/app/services/rag.py` | Modify | ask_with_rag_stream yield dict 格式 |
| `backend/tests/test_llm_stream.py` | Create | 流式 yield dict 格式测试 |
| `frontend/src/api/chat.js` | Modify | 新增 sendChatStream SSE 函数 |
| `frontend/src/components/ChatMessage.vue` | Modify | 重写：用户纯文本靠右 + AI 头像无气泡 + 思考折叠面板 |
| `frontend/src/views/ChatView.vue` | Modify | 深色侧边栏 + 流式逻辑 + 模型选择 |
| `frontend/src/views/LoginView.vue` | Modify | 深色背景 + DeepSeek 蓝色调 |
| `frontend/src/style.css` | Modify | 全局样式重置 |
| `frontend/src/__tests__/ChatMessage.test.js` | Modify | 更新组件测试适配新样式 |

---

### Task 1: 后端 — llm.py 透传 reasoning_content

**Files:**
- Modify: `backend/app/services/llm.py:87-94` (chat_completion)
- Modify: `backend/app/services/llm.py:125-139` (chat_completion_stream)

- [ ] **Step 1: 修改 chat_completion 返回 reasoning_content**

将 `chat_completion` 的返回类型从 `str` 改为 `tuple[str, str]`，返回 `(reasoning_content, answer)`。

当前代码（第 87-94 行）：
```python
response = client.chat.completions.create(
    model=model or settings.OPENAI_MODEL,
    messages=messages,
    temperature=0.7,
)
return response.choices[0].message.content
```

替换为：
```python
response = client.chat.completions.create(
    model=model or settings.OPENAI_MODEL,
    messages=messages,
    temperature=0.7,
)
msg = response.choices[0].message
reasoning = getattr(msg, "reasoning_content", None) or ""
answer = msg.content or ""
return reasoning, answer
```

- [ ] **Step 2: 修改 chat_completion_stream yield dict**

当前代码（第 125-139 行）：
```python
response = client.chat.completions.create(
    model=model or settings.OPENAI_MODEL,
    messages=messages,
    temperature=0.7,
    stream=True,
)

for chunk in response:
    if chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

替换为：
```python
response = client.chat.completions.create(
    model=model or settings.OPENAI_MODEL,
    messages=messages,
    temperature=0.7,
    stream=True,
)

for chunk in response:
    delta = chunk.choices[0].delta
    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning:
        yield {"type": "reasoning", "content": reasoning}
    elif delta.content:
        yield {"type": "answer", "content": delta.content}
```

- [ ] **Step 3: 更新 generate_title 和 generate_summary 调用方**

`generate_title`（第 158 行）和 `generate_summary`（第 178 行）都调用了 `chat_completion`，现在返回 tuple 了。

将第 158 行：
```python
title = chat_completion([{"role": "user", "content": prompt}])
```
替换为：
```python
_, title = chat_completion([{"role": "user", "content": prompt}])
```

将第 178 行：
```python
return chat_completion([{"role": "user", "content": prompt}])
```
替换为：
```python
_, summary = chat_completion([{"role": "user", "content": prompt}])
return summary
```

- [ ] **Step 4: 运行现有测试确认未破坏**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short
```
Expected: 所有现有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm.py
git commit -m "feat(llm): yield dict format with reasoning_content in stream, return tuple from chat_completion"
```

---

### Task 2: 后端 — langchain_agent.py 和 rag.py 适配 dict 格式

**Files:**
- Modify: `backend/app/services/langchain_agent.py:59-75` (run_agent_stream)
- Modify: `backend/app/services/rag.py:115-143` (ask_with_rag_stream)

- [ ] **Step 1: 修改 run_agent_stream yield dict**

当前代码（第 67-75 行）：
```python
async for event in agent.astream(
    {"messages": messages},
    stream_mode=["messages"],
):
    event_type, event_data = event
    if event_type == "messages" and event_data:
        chunk = event_data[0]
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content
```

替换为：
```python
async for event in agent.astream(
    {"messages": messages},
    stream_mode=["messages"],
):
    event_type, event_data = event
    if event_type == "messages" and event_data:
        chunk = event_data[0]
        if hasattr(chunk, "content") and chunk.content:
            yield {"type": "answer", "content": chunk.content}
```

- [ ] **Step 2: 修改 ask_with_rag_stream yield dict**

当前代码（第 143 行）：
```python
yield from chat_completion_stream(messages)
```

`chat_completion_stream` 现在 yield dict，所以 `ask_with_rag_stream` 会自动传递 dict。无需修改这行。

但需要确认 `ask_with_rag`（非流式，第 81-112 行）也适配 `chat_completion` 返回 tuple：

当前第 112 行：
```python
return chat_completion(messages)
```

替换为：
```python
_, answer = chat_completion(messages)
return answer
```

- [ ] **Step 3: 运行测试**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/langchain_agent.py backend/app/services/rag.py
git commit -m "feat: adapt agent and rag streams to dict format for reasoning support"
```

---

### Task 3: 后端 — chat.py SSE 序列化 + schema 更新

**Files:**
- Modify: `backend/app/api/chat.py:180-248` (chat_stream generate)
- Modify: `backend/app/api/chat.py:134-169` (chat endpoint)
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: 更新 ChatRequest schema**

当前 `backend/app/schemas/chat.py`：
```python
class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None
    mode: Literal["normal", "agent"] = "normal"
```

替换整个文件为：
```python
from typing import Literal

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    kb_id: int | None = None
    session_id: int | None = None
    mode: Literal["normal", "agent"] = "normal"
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    kb_id: int | None = None
```

- [ ] **Step 2: 修改 chat_stream 的 generate() 函数处理 dict chunk**

当前 `chat.py` 的 `generate()` 函数中所有流式循环都写为 `yield f"data: {chunk}\n\n"`，其中 chunk 现在是 dict。

在 `generate()` 函数开头添加 `import json`（实际加在文件顶部）。

修改所有流式 yield 点（4 处）：

**Agent 分支**（第 203-205 行）：
```python
chunk = loop.run_until_complete(agen.__anext__())
full_answer += chunk
yield f"data: {chunk}\n\n"
```
替换为：
```python
chunk = loop.run_until_complete(agen.__anext__())
full_answer += chunk["content"]
yield f"data: {json.dumps(chunk)}\n\n"
```

**RAG 分支**（第 213-217 行）：
```python
for chunk in ask_with_rag_stream(...):
    full_answer += chunk
    yield f"data: {chunk}\n\n"
```
替换为：
```python
for chunk in ask_with_rag_stream(...):
    full_answer += chunk["content"]
    yield f"data: {json.dumps(chunk)}\n\n"
```

**带上下文的普通对话分支**（第 229-231 行）：
```python
for chunk in llm_stream(messages):
    full_answer += chunk
    yield f"data: {chunk}\n\n"
```
替换为：
```python
for chunk in llm_stream(messages):
    full_answer += chunk["content"]
    yield f"data: {json.dumps(chunk)}\n\n"
```

**无上下文的普通对话分支**（第 235-237 行）：
```python
for chunk in llm_stream([{"role": "user", "content": data.question}]):
    full_answer += chunk
    yield f"data: {chunk}\n\n"
```
替换为：
```python
for chunk in llm_stream([{"role": "user", "content": data.question}]):
    full_answer += chunk["content"]
    yield f"data: {json.dumps(chunk)}\n\n"
```

- [ ] **Step 3: 在文件顶部添加 json import**

当前第 11 行：
```python
from fastapi import APIRouter, Depends, HTTPException
```

在这行之前添加：
```python
import json
```

- [ ] **Step 4: 运行测试**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/chat.py backend/app/schemas/chat.py
git commit -m "feat(chat): SSE serialize dict chunks, add stream field to ChatRequest"
```

---

### Task 4: 后端 — 测试 reasoning_content 流式格式

**Files:**
- Create: `backend/tests/test_llm_stream.py`

- [ ] **Step 1: 创建流式 dict 格式测试**

```python
"""LLM 流式服务测试 — 验证 yield dict 格式"""

from unittest.mock import MagicMock, patch


class TestChatCompletionStreamDictFormat:
    @patch("app.services.llm.client")
    def test_yields_answer_dict(self, mock_client):
        """普通回答 chunk 应 yield {type: answer}"""
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "你好"
        # reasoning_content 不存在时 getattr 返回 None
        del mock_chunk.choices[0].delta.reasoning_content

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        from app.services.llm import chat_completion_stream

        results = list(chat_completion_stream([{"role": "user", "content": "hi"}]))
        assert len(results) == 1
        assert results[0] == {"type": "answer", "content": "你好"}

    @patch("app.services.llm.client")
    def test_yields_reasoning_dict(self, mock_client):
        """reasoning_content chunk 应 yield {type: reasoning}"""
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = None
        mock_chunk.choices[0].delta.reasoning_content = "让我想想..."

        mock_client.chat.completions.create.return_value = iter([mock_chunk])

        from app.services.llm import chat_completion_stream

        results = list(chat_completion_stream([{"role": "user", "content": "hi"}]))
        assert len(results) == 1
        assert results[0] == {"type": "reasoning", "content": "让我想想..."}


class TestChatCompletionReturnsTuple:
    @patch("app.services.llm.client")
    def test_returns_reasoning_and_answer(self, mock_client):
        """chat_completion 应返回 (reasoning, answer) tuple"""
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        mock_msg.reasoning_content = "这是思考"
        mock_response.choices = [MagicMock(message=mock_msg)]

        mock_client.chat.completions.create.return_value = mock_response

        from app.services.llm import chat_completion

        reasoning, answer = chat_completion([{"role": "user", "content": "hi"}])
        assert reasoning == "这是思考"
        assert answer == "这是回答"

    @patch("app.services.llm.client")
    def test_returns_empty_reasoning_when_none(self, mock_client):
        """reasoning_content 为空时返回空字符串"""
        mock_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        del mock_msg.reasoning_content  # 触发 getattr 返回 None
        mock_response.choices = [MagicMock(message=mock_msg)]

        mock_client.chat.completions.create.return_value = mock_response

        from app.services.llm import chat_completion

        reasoning, answer = chat_completion([{"role": "user", "content": "hi"}])
        assert reasoning == ""
        assert answer == "这是回答"
```

- [ ] **Step 2: 运行新测试**

```bash
cd F:/IntraAI && python -m pytest backend/tests/test_llm_stream.py -v --tb=short
```
Expected: 4 PASS

- [ ] **Step 3: 运行全部后端测试**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short
```
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_llm_stream.py
git commit -m "test: add llm stream dict format and tuple return tests"
```

---

### Task 5: 前端 — chat.js 新增 sendChatStream

**Files:**
- Modify: `frontend/src/api/chat.js`

- [ ] **Step 1: 添加 sendChatStream 函数**

在现有 `sendChat` 函数之后追加：

```javascript
/**
 * 发送流式对话请求（SSE）
 *
 * 使用 fetch + ReadableStream 处理 Server-Sent Events。
 * 返回 AsyncGenerator，调用方用 for await...of 消费。
 *
 * 每次 yield 一个对象：
 *   { type: "reasoning", content: "..." }  — 思考过程片段
 *   { type: "answer", content: "..." }     — 回答片段
 *
 * @param {Object} data - 请求数据 { question, kb_id, session_id, mode }
 * @returns {AsyncGenerator} 流式数据生成器
 */
export async function* sendChatStream(data) {
  const token = localStorage.getItem('token')
  const baseURL = import.meta.env.PROD ? '' : 'http://localhost:8000'
  const res = await fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw new Error(`Stream request failed: ${res.status}`)
  }

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
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') return
        if (raw === '[ERROR]') throw new Error('Stream error')
        try {
          yield JSON.parse(raw)
        } catch {
          yield { type: 'answer', content: raw }
        }
      }
    }
  }
}
```

- [ ] **Step 2: 前端 lint 检查**

```bash
cd F:/IntraAI/frontend && npx eslint src/api/chat.js
```
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/chat.js
git commit -m "feat(chat): add sendChatStream SSE function"
```

---

### Task 6: 前端 — ChatMessage.vue 重写

**Files:**
- Modify: `frontend/src/components/ChatMessage.vue`

- [ ] **Step 1: 重写整个组件**

替换整个文件：

```vue
<template>
  <div :class="['message', message.role]">
    <!-- AI 头像（仅 assistant 显示） -->
    <div v-if="message.role === 'assistant'" class="avatar">AI</div>

    <div class="message-body">
      <!-- 用户消息：纯文本靠右 -->
      <div v-if="message.role === 'user'" class="user-content">
        {{ message.content }}
      </div>

      <!-- AI 消息 -->
      <template v-else>
        <!-- 思考过程折叠面板 -->
        <div v-if="message.reasoning" class="thinking-panel">
          <div class="thinking-header" @click="toggleThinking">
            <span class="thinking-arrow">{{ showThinking ? '▾' : '▸' }}</span>
            <span class="thinking-label">
              已思考 {{ message.reasoning_time || 0 }} 秒
            </span>
            <span v-if="message.streaming" class="thinking-spinner"></span>
          </div>
          <div v-show="showThinking" class="thinking-content">
            {{ message.reasoning }}
          </div>
        </div>

        <!-- 回答内容：Markdown 渲染 -->
        <div class="content" v-html="renderedContent"></div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt()

const props = defineProps({
  message: Object,
})

const showThinking = ref(false)

// 流式中展开思考面板，结束后 0.5s 自动收起
watch(
  () => props.message.streaming,
  (streaming, oldStreaming) => {
    if (streaming) {
      showThinking.value = true
    } else if (oldStreaming === true) {
      setTimeout(() => {
        showThinking.value = false
      }, 500)
    }
  },
  { immediate: true }
)

function toggleThinking() {
  showThinking.value = !showThinking.value
}

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return md.render(props.message.content || '')
  }
  return props.message.content
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  padding: 8px 0;
}

/* 用户消息靠右，无头像 */
.message.user {
  justify-content: flex-end;
}

.user-content {
  max-width: 70%;
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a2e;
  text-align: right;
  white-space: pre-wrap;
  word-break: break-word;
}

/* AI 头像 */
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: #4D6BFE;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.message-body {
  flex: 1;
  max-width: 70%;
}

/* 思考过程面板 */
.thinking-panel {
  margin-bottom: 12px;
  border-left: 2px solid #4D6BFE;
  padding-left: 12px;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #888;
  font-size: 13px;
  padding: 4px 0;
  user-select: none;
}

.thinking-header:hover {
  color: #555;
}

.thinking-arrow {
  font-size: 12px;
}

.thinking-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #ddd;
  border-top-color: #4D6BFE;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.thinking-content {
  color: #888;
  font-style: italic;
  font-size: 14px;
  line-height: 1.6;
  padding: 8px 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* AI 回答内容 */
.content {
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a2e;
}

/* Markdown 渲染后的代码块样式 */
.content :deep(pre) {
  background: #f4f3ec;
  border-radius: 6px;
  padding: 12px 16px;
  overflow-x: auto;
}

.content :deep(code) {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 13px;
}

.content :deep(p) {
  margin: 0 0 8px;
}

.content :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
```

- [ ] **Step 2: 更新现有测试**

当前测试引用 `.avatar` 检查用户消息，但新设计中用户消息不再有头像。替换 `frontend/src/__tests__/ChatMessage.test.js`：

```javascript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '../components/ChatMessage.vue'

describe('ChatMessage', () => {
  it('用户消息靠右显示，无头像', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'user', content: '你好' } },
    })
    expect(wrapper.find('.message.user').exists()).toBe(true)
    expect(wrapper.find('.avatar').exists()).toBe(false)
    expect(wrapper.find('.user-content').text()).toBe('你好')
  })

  it('AI 消息靠左显示，有头像', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '你好！' } },
    })
    expect(wrapper.find('.message.assistant').exists()).toBe(true)
    expect(wrapper.find('.avatar').text()).toBe('AI')
  })

  it('用户消息不经过 Markdown 渲染', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'user', content: '**加粗**' } },
    })
    expect(wrapper.find('.user-content').text()).toBe('**加粗**')
  })

  it('AI 消息经过 Markdown 渲染为 HTML', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '**加粗**' } },
    })
    expect(wrapper.find('.content').html()).toContain('<strong>加粗</strong>')
  })

  it('有 reasoning 时显示思考面板', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '回答',
          reasoning: '我在思考',
          reasoning_time: 3,
          streaming: false,
        },
      },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(true)
    expect(wrapper.find('.thinking-content').text()).toBe('我在思考')
  })

  it('无 reasoning 时不显示思考面板', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '回答' } },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(false)
  })

  it('流式中思考面板展开', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '',
          reasoning: '思考中...',
          streaming: true,
        },
      },
    })
    expect(wrapper.find('.thinking-content').isVisible()).toBe(true)
  })
})
```

- [ ] **Step 3: 运行前端测试**

```bash
cd F:/IntraAI/frontend && npx vitest run
```
Expected: 7 PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChatMessage.vue frontend/src/__tests__/ChatMessage.test.js
git commit -m "feat(ChatMessage): rewrite with thinking panel, user plain text, AI avatar style"
```

---

### Task 7: 前端 — ChatView.vue 深色侧边栏 + 流式逻辑

**Files:**
- Modify: `frontend/src/views/ChatView.vue`

- [ ] **Step 1: 重写模板部分**

替换整个 `<template>` 和 `<style>` 部分，保留 `<script setup>` 中的逻辑并扩展。

完整替换整个文件：

```vue
<template>
  <div class="app-layout">
    <!-- 深色侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">IntraAI</div>
        <button class="new-chat-btn" @click="handleNewSession">+ 新建对话</button>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: currentSessionId === s.id }]"
            @click="handleSelectSession(s.id)"
          >
            <span class="session-title">{{ s.title }}</span>
            <button class="delete-btn" @click.stop="handleDeleteSession(s.id)">X</button>
          </div>
          <div v-if="sessions.length === 0" class="empty-hint">暂无对话</div>
        </div>
      </div>
      <div class="sidebar-bottom">
        <div class="nav-links">
          <router-link to="/" class="nav-link active">对话</router-link>
          <router-link to="/knowledge" class="nav-link">知识库</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/admin" class="nav-link">管理</router-link>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 消息列表 -->
      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="empty-chat">
          <h2>IntraAI 知识助手</h2>
          <p>选择知识库后开始提问，或直接对话</p>
        </div>
        <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
      </div>

      <!-- 输入区 -->
      <div class="input-section">
        <!-- 工具栏 -->
        <div class="toolbar">
          <a-select
            v-model:value="selectedModel"
            :options="modelOptions"
            size="small"
            style="width: 160px"
            bordered="false"
          />
          <a-select
            v-model:value="selectedKb"
            placeholder="选择知识库"
            :options="kbOptions"
            allow-clear
            size="small"
            style="width: 160px"
          />
          <div class="stream-toggle">
            <span>流式</span>
            <a-switch v-model:checked="useStream" size="small" />
          </div>
        </div>
        <!-- 输入框 -->
        <div class="input-box">
          <a-textarea
            v-model:value="question"
            placeholder="输入问题..."
            :auto-size="{ minRows: 1, maxRows: 6 }"
            @keydown.enter.exact.prevent="handleSend"
            :bordered="false"
          />
          <a-button
            type="primary"
            :loading="loading"
            :disabled="!question.trim()"
            @click="handleSend"
            class="send-btn"
          >
            发送
          </a-button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases } from '../api/knowledge'
import { sendChat, sendChatStream } from '../api/chat'
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
const useStream = ref(true)
const selectedModel = ref('mimo-v2-pro')
const modelOptions = [
  { label: 'MiMo v2 Pro', value: 'mimo-v2-pro' },
  { label: 'MiMo v2 Lite', value: 'mimo-v2-lite' },
]

const sessions = ref([])
const currentSessionId = ref(null)

async function fetchSessions() {
  const res = await listSessions()
  sessions.value = res.data
}

async function fetchKbs() {
  const res = await listKnowledgeBases()
  kbOptions.value = res.data.map(kb => ({ label: kb.name, value: kb.id }))
}

async function handleNewSession() {
  const res = await createSession()
  const newSession = res.data
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  messages.value = []
}

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

async function handleSend() {
  if (!question.value.trim() || loading.value) return

  const q = question.value.trim()
  question.value = ''
  messages.value.push({ role: 'user', content: q })
  loading.value = true

  await nextTick()
  scrollToBottom()

  if (useStream.value) {
    await handleStreamSend(q)
  } else {
    await handleNormalSend(q)
  }
}

async function handleStreamSend(q) {
  messages.value.push({
    role: 'assistant',
    content: '',
    reasoning: '',
    reasoning_time: 0,
    streaming: true,
  })
  const msg = messages.value[messages.value.length - 1]
  let reasoningStartTime = null

  try {
    for await (const chunk of sendChatStream({
      question: q,
      kb_id: selectedKb.value,
      session_id: currentSessionId.value,
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
  } catch {
    message.error('发送失败')
  } finally {
    msg.streaming = false
    loading.value = false
    fetchSessions()
  }
}

async function handleNormalSend(q) {
  try {
    const res = await sendChat({
      question: q,
      kb_id: selectedKb.value,
      session_id: currentSessionId.value,
    })
    messages.value.push({ role: 'assistant', content: res.data.answer })
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
.app-layout {
  display: flex;
  height: 100vh;
}

/* ===== 深色侧边栏 ===== */
.sidebar {
  width: 260px;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-top {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px;
}

.sidebar-logo {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 16px;
  padding: 4px 0;
}

.new-chat-btn {
  width: 100%;
  padding: 10px;
  background: #4D6BFE;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  margin-bottom: 16px;
}

.new-chat-btn:hover {
  background: #3d5be0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 2px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #ccc;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.session-item.active {
  background: rgba(77, 107, 254, 0.2);
  color: #fff;
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  opacity: 0;
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.empty-hint {
  color: #666;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.sidebar-bottom {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.nav-link {
  color: #aaa;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.nav-link:hover,
.nav-link.active {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.logout-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #aaa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.logout-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* ===== 主内容区 ===== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f7f7f8;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px calc((100% - 720px) / 2);
}

.empty-chat {
  text-align: center;
  padding: 80px 20px 40px;
  color: #999;
}

.empty-chat h2 {
  color: #333;
  font-size: 24px;
  margin-bottom: 8px;
}

/* ===== 输入区 ===== */
.input-section {
  padding: 0 calc((100% - 720px) / 2) 24px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  padding: 0 4px;
}

.stream-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #888;
  margin-left: auto;
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 12px 16px;
  transition: border-color 0.2s;
}

.input-box:focus-within {
  border-color: #4D6BFE;
}

.input-box :deep(.ant-input) {
  font-size: 15px;
  padding: 0;
  border: none !important;
  box-shadow: none !important;
}

.send-btn {
  flex-shrink: 0;
  border-radius: 8px;
}
</style>
```

- [ ] **Step 2: 验证前端 lint**

```bash
cd F:/IntraAI/frontend && npx eslint src/views/ChatView.vue
```
Expected: 无错误

- [ ] **Step 3: 运行前端测试**

```bash
cd F:/IntraAI/frontend && npx vitest run
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ChatView.vue
git commit -m "feat(ChatView): dark sidebar, stream toggle, model selector, sticky input"
```

---

### Task 8: 前端 — LoginView.vue 色调微调

**Files:**
- Modify: `frontend/src/views/LoginView.vue:379-393` (style section)

- [ ] **Step 1: 更新登录页样式**

将 `<style scoped>` 部分（第 343-394 行）替换为：

```css
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #1a1a2e;
}

.login-card {
  width: 400px;
  border-radius: 12px;
}

.login-card :deep(.ant-card-head-title) {
  font-size: 20px;
  font-weight: 600;
}

.login-card :deep(.ant-btn-primary) {
  background: #4D6BFE;
  border-color: #4D6BFE;
}

.login-card :deep(.ant-btn-primary:hover) {
  background: #3d5be0;
  border-color: #3d5be0;
}

.login-card :deep(a) {
  color: #4D6BFE;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/LoginView.vue
git commit -m "style(LoginView): deep background and DeepSeek blue accent color"
```

---

### Task 9: 前端 — style.css 全局样式重置

**Files:**
- Modify: `frontend/src/style.css`

- [ ] **Step 1: 替换全局样式**

当前 `style.css` 包含大量 Vite 模板的默认样式（hero、counter 等），全部替换为聊天应用的极简 reset：

```css
:root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #f7f7f8;
  color: #1a1a2e;
}

#app {
  width: 100%;
  min-height: 100vh;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/style.css
git commit -m "style: reset global styles for chat application"
```

---

### Task 10: KnowledgeView / AdminView 导航同步

**Files:**
- Modify: `frontend/src/views/KnowledgeView.vue`
- Modify: `frontend/src/views/AdminView.vue`

- [ ] **Step 1: 重写 KnowledgeView 布局**

将 KnowledgeView 的 `<template>` 和 `<style>` 部分改为使用与 ChatView 相同的深色侧边栏。

替换 `<template>` 开头（第 7-37 行的 layout 部分）和对应的 `<style>` 部分。

在 KnowledgeView 中：
- 去掉 `<a-layout-header>` 和 `<a-menu theme="dark" mode="horizontal">`
- 添加与 ChatView 相同的 `<aside class="sidebar">` 结构
- 将 `<a-layout-content>` 改为 `<main class="main-content">`

完整替换 `<template>` 部分：

```vue
<template>
  <div class="app-layout">
    <!-- 深色侧边栏（与 ChatView 一致） -->
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">IntraAI</div>
      </div>
      <div class="sidebar-bottom">
        <div class="nav-links">
          <router-link to="/" class="nav-link">对话</router-link>
          <router-link to="/knowledge" class="nav-link active">知识库</router-link>
          <router-link v-if="authStore.user?.is_admin" to="/admin" class="nav-link">管理</router-link>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content-knowledge">
      <div class="knowledge-container">
        <a-card title="知识库管理">
          <template #extra>
            <a-button type="primary" @click="showCreate = true">新建知识库</a-button>
          </template>
          <!-- 保留现有的表格和功能 -->
```

在 `<style scoped>` 中添加：

```css
.app-layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 260px;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-top {
  flex: 1;
  padding: 16px;
}

.sidebar-logo {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  padding: 4px 0;
}

.sidebar-bottom {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.nav-link {
  color: #aaa;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.nav-link:hover,
.nav-link.active {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.logout-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #aaa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.logout-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

.main-content-knowledge {
  flex: 1;
  background: #f7f7f8;
  overflow-y: auto;
  padding: 24px;
}

.knowledge-container {
  max-width: 960px;
  margin: 0 auto;
}
```

- [ ] **Step 2: 重写 AdminView 布局**

AdminView 也做同样的改动：去掉顶部导航栏，改为深色侧边栏。

替换 `<template>` 开头部分（第 7-20 行的 header 部分）：

```vue
<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">IntraAI</div>
      </div>
      <div class="sidebar-bottom">
        <div class="nav-links">
          <router-link to="/" class="nav-link">对话</router-link>
          <router-link to="/knowledge" class="nav-link">知识库</router-link>
          <router-link to="/admin" class="nav-link active">管理</router-link>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </aside>

    <main class="main-content-admin">
```

在 `<style scoped>` 中添加与 KnowledgeView 相同的 `.app-layout`, `.sidebar`, `.sidebar-top`, `.sidebar-logo`, `.sidebar-bottom`, `.nav-links`, `.nav-link`, `.logout-btn` 样式，以及：

```css
.main-content-admin {
  flex: 1;
  display: flex;
  background: #f7f7f8;
  overflow: hidden;
}
```

注意：AdminView 的左侧子菜单（`a-layout-sider`）保留，它是管理页面内部的 tab 切换，不是主导航。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/KnowledgeView.vue frontend/src/views/AdminView.vue
git commit -m "style: sync dark sidebar navigation to KnowledgeView and AdminView"
```

---

### Task 11: 端到端验证

- [ ] **Step 1: 运行全部后端测试**

```bash
cd F:/IntraAI && python -m pytest backend/tests/ -v --tb=short
```
Expected: 全部 PASS

- [ ] **Step 2: 运行全部前端测试**

```bash
cd F:/IntraAI/frontend && npx vitest run
```
Expected: 全部 PASS

- [ ] **Step 3: 前端 lint 检查**

```bash
cd F:/IntraAI/frontend && npx eslint src/ --ext .js,.vue
```
Expected: 无错误

- [ ] **Step 4: 启动后端验证 SSE 接口**

```bash
cd F:/IntraAI/backend && python -m uvicorn app.main:app --reload --port 8000
```

在另一个终端测试：
```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "你好"}'
```
Expected: SSE 响应中包含 `data: {"type":"reasoning",...}` 和 `data: {"type":"answer",...}` 格式的行

- [ ] **Step 5: 启动前端验证 UI**

```bash
cd F:/IntraAI/frontend && npm run dev
```

在浏览器中打开 http://localhost:5173，验证：
1. 登录页：深色背景 + DeepSeek 蓝色按钮
2. 对话页：深色侧边栏 + 消息无气泡 + 用户靠右 + AI 左头像
3. 发送消息后：思考面板出现 → 展开 → 回答完成后自动收起
4. 切换流式开关：非流式模式仍正常工作
5. 知识库/管理页面：深色侧边栏一致

- [ ] **Step 6: 最终 Commit（如有小修小补）**

```bash
git add -A && git commit -m "fix: minor UI polish after E2E verification"
```

---

## Self-Review

**Spec coverage:**
- reasoning_content 透传: Task 1-2
- SSE dict 序列化: Task 3
- 流式前端函数: Task 5
- 消息样式重写 + 思考面板: Task 6
- 深色侧边栏 + 流式逻辑: Task 7
- LoginView 色调: Task 8
- 全局样式: Task 9
- KnowledgeView/AdminView 导航: Task 10
- 测试: Task 4 + Task 6 Step 2 + Task 11

**No placeholders found.** All steps contain exact code and file paths.

**Type consistency:** dict 格式 `{"type": "reasoning"|"answer", "content": "..."}` 在 Task 1 (llm.py) 定义 → Task 2 (agent/rag) 保持一致 → Task 3 (chat.py) SSE 序列化 → Task 5 (chat.js) 前端解析 → Task 6 (ChatMessage) 消费。全链路一致。
