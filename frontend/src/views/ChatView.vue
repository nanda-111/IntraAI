<template>
  <AppLayout>
    <template #sidebar-extra>
      <button
        class="new-chat-btn"
        @click="handleNewSession"
      >
        + 新建对话
      </button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          :class="['session-item', { active: currentSessionId === s.id }]"
          @click="handleSelectSession(s.id)"
        >
          <span class="session-title">{{ s.title }}</span>
          <button
            class="delete-btn"
            @click.stop="handleDeleteSession(s.id)"
          >
            X
          </button>
        </div>
        <div
          v-if="sessions.length === 0"
          class="empty-hint"
        >
          暂无对话
        </div>
      </div>
    </template>

    <div
      ref="messagesRef"
      class="messages"
    >
      <div
        v-if="messages.length === 0"
        class="empty-chat"
      >
        <h2>IntraAI 知识助手</h2>
        <p>选择知识库后开始提问，或直接对话</p>
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :message="msg"
      />
    </div>

    <div class="input-section">
      <div class="toolbar">
        <a-select
          v-model:value="selectedModel"
          :options="modelOptions"
          size="small"
          style="width: 160px"
          :bordered="false"
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
          <a-switch
            v-model:checked="useStream"
            size="small"
          />
        </div>
      </div>
      <div class="input-box">
        <a-textarea
          v-model:value="question"
          placeholder="输入问题..."
          :auto-size="{ minRows: 1, maxRows: 6 }"
          :bordered="false"
          @keydown.enter.exact.prevent="handleSend"
        />
        <a-button
          type="primary"
          :loading="loading"
          :disabled="!question.trim()"
          class="send-btn"
          @click="handleSend"
        >
          发送
        </a-button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'
import { listKnowledgeBases } from '../api/knowledge'
import { sendChat, sendChatStream } from '../api/chat'
import { createSession, listSessions, getSession, deleteSession } from '../api/session'
import ChatMessage from '../components/ChatMessage.vue'

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

  if (!currentSessionId.value) {
    const res = await createSession()
    const newSession = res.data
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
  }

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
  // reasoning 初始为 null，模板中 null 才表示"还没有思考内容"
  // 空字符串 '' 表示"有思考过程但内容为空"，不应用于初始状态
  messages.value.push({
    role: 'assistant',
    content: '',
    reasoning: null,
    reasoning_time: 0,
    reasoning_done: false,
    streaming: true,
  })
  const msg = messages.value[messages.value.length - 1]
  let reasoningStartTime = null

  // 双缓冲 + rAF：完全消除 chunk 级别的 Vue 响应式触发
  let writeBuffer = ''
  let rafId = null

  function flushBuffer() {
    if (!writeBuffer) {
      rafId = null
      return
    }
    // 原子性地将缓冲内容赋值给 reasoning（一次性触发一次 Vue 更新）
    msg.reasoning = (msg.reasoning || '') + writeBuffer
    writeBuffer = ''
    rafId = null
  }

  function scheduleFlush() {
    if (rafId) return
    rafId = requestAnimationFrame(flushBuffer)
  }

  const gen = sendChatStream({
    question: q,
    kb_id: selectedKb.value,
    session_id: currentSessionId.value,
  })

  try {
    for (;;) {
      const { value: chunk, done } = await gen.next()
      if (done) break

      if (chunk.type === 'reasoning') {
        if (!reasoningStartTime) reasoningStartTime = Date.now()
        writeBuffer += chunk.content
        scheduleFlush()
      } else if (chunk.type === 'answer') {
        // 思考阶段结束：先把残余 reasoning 缓冲一次性刷出
        if (writeBuffer) {
          msg.reasoning = (msg.reasoning || '') + writeBuffer
          writeBuffer = ''
          if (rafId) {
            cancelAnimationFrame(rafId)
            rafId = null
          }
        }
        // 标记思考完成 → 模板中 v-if 生效，回答区域开始渲染
        if (!msg.reasoning_done) {
          msg.reasoning_done = true
          if (reasoningStartTime && !msg.reasoning_time) {
            msg.reasoning_time = Math.round((Date.now() - reasoningStartTime) / 1000)
          }
        }
        msg.content += chunk.content
      }
    }
  } catch {
    message.error('发送失败')
  } finally {
    // 最终清理：刷出所有残余缓冲
    if (writeBuffer) {
      msg.reasoning = (msg.reasoning || '') + writeBuffer
      writeBuffer = ''
    }
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    if (reasoningStartTime && !msg.reasoning_time) {
      msg.reasoning_time = Math.round((Date.now() - reasoningStartTime) / 1000)
    }
    msg.reasoning_done = true
    msg.streaming = false
    loading.value = false
    try { await gen.return() } catch { /* ignore */ }
    try { await fetchSessions() } catch { /* ignore */ }
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

onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
  fetchSessions()
})
</script>

<style scoped>
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
