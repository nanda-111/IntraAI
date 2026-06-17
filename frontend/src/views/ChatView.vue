<template>
  <AppLayout>
    <template #sidebar-extra>
      <button
        class="new-chat-btn"
        @click="handleNewSession"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <line
            x1="12"
            y1="5"
            x2="12"
            y2="19"
          />
          <line
            x1="5"
            y1="12"
            x2="19"
            y2="12"
          />
        </svg>
        新建对话
      </button>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          :class="['session-item', { active: currentSessionId === s.id }]"
          @click="handleSelectSession(s.id)"
        >
          <svg
            class="session-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span class="session-title">{{ s.title }}</span>
          <button
            class="delete-btn"
            title="删除对话"
            @click.stop="handleDeleteSession(s.id)"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <line
                x1="18"
                y1="6"
                x2="6"
                y2="18"
              />
              <line
                x1="6"
                y1="6"
                x2="18"
                y2="18"
              />
            </svg>
          </button>
        </div>
        <div
          v-if="sessions.length === 0"
          class="empty-hint"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            style="width: 28px; height: 28px; margin-bottom: 8px; opacity: 0.4"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
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
        <div class="empty-logo">
          AI
        </div>
        <h2>IntraAI 知识助手</h2>
        <p>选择知识库后开始提问，或直接对话</p>
        <div class="quick-actions">
          <button
            class="quick-btn"
            @click="question = '你好，请介绍一下你自己'"
          >
            你好，请介绍一下你自己
          </button>
          <button
            class="quick-btn"
            @click="question = '帮我总结一下知识库的内容'"
          >
            帮我总结知识库内容
          </button>
        </div>
      </div>
      <ChatMessage
        v-for="(msg, i) in messages"
        :key="i"
        :message="msg"
      />
    </div>

    <div class="input-section">
      <div class="input-container">
        <div class="toolbar">
          <a-select
            v-model:value="selectedModel"
            :options="modelOptions"
            size="small"
            class="toolbar-select"
            :bordered="false"
          />
          <div class="toolbar-divider" />
          <a-select
            v-model:value="selectedKb"
            placeholder="知识库"
            :options="kbOptions"
            allow-clear
            size="small"
            class="toolbar-select"
            :bordered="false"
          />
          <div class="toolbar-right">
            <span class="stream-label">流式</span>
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
            :auto-size="{ minRows: 1, maxRows: 5 }"
            :bordered="false"
            @keydown.enter.exact.prevent="handleSend"
          />
          <button
            class="send-btn"
            :disabled="!question.trim() || loading"
            @click="handleSend"
          >
            <span
              v-if="loading"
              class="send-spinner"
            />
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <line
                x1="22"
                y1="2"
                x2="11"
                y2="13"
              />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div class="input-hint">
          Enter 发送 · Shift + Enter 换行
        </div>
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
const selectedModel = ref('mimo-v2.5-pro')
const modelOptions = [
  { label: 'MiMo v2.5 Pro', value: 'mimo-v2.5-pro' },
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
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
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

  let writeBuffer = ''
  let rafId = null

  function flushBuffer() {
    if (!writeBuffer) { rafId = null; return }
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
    model: selectedModel.value,
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
        if (writeBuffer) {
          msg.reasoning = (msg.reasoning || '') + writeBuffer
          writeBuffer = ''
          if (rafId) { cancelAnimationFrame(rafId); rafId = null }
        }
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
    if (writeBuffer) {
      msg.reasoning = (msg.reasoning || '') + writeBuffer
      writeBuffer = ''
    }
    if (rafId) { cancelAnimationFrame(rafId); rafId = null }
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
      model: selectedModel.value,
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
/* ==================== Sidebar session list ==================== */
.new-chat-btn {
  width: 100%;
  padding: 9px 14px;
  background: var(--sidebar-surface);
  color: var(--sidebar-text-active);
  border: 1px solid var(--sidebar-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all var(--transition-fast);
}

.new-chat-btn svg {
  width: 15px;
  height: 15px;
}

.new-chat-btn:hover {
  background: var(--sidebar-surface-hover);
  border-color: rgba(255, 255, 255, 0.12);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  margin: 0 -16px;
  padding: 0 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 1px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  color: var(--sidebar-text);
  transition: all var(--transition-fast);
}

.session-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  opacity: 0.5;
}

.session-item:hover {
  background: var(--sidebar-surface-hover);
  color: var(--sidebar-text-active);
}

.session-item:hover .session-icon {
  opacity: 0.8;
}

.session-item.active {
  background: var(--sidebar-surface-active);
  color: var(--sidebar-text-active);
}

.session-item.active .session-icon {
  opacity: 1;
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
  color: var(--sidebar-text);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.delete-btn svg {
  width: 13px;
  height: 13px;
}

.session-item:hover .delete-btn {
  opacity: 0.6;
}

.delete-btn:hover {
  opacity: 1 !important;
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.1);
}

.empty-hint {
  color: var(--sidebar-text);
  font-size: 12px;
  text-align: center;
  padding: 32px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  opacity: 0.6;
}

/* ==================== Messages area ==================== */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px calc((100% - 760px) / 2);
  scroll-behavior: smooth;
}

.empty-chat {
  text-align: center;
  padding: 100px 20px 40px;
}

.empty-logo {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, var(--color-primary), #7c5cfc);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin: 0 auto 20px;
  box-shadow: 0 4px 24px rgba(77, 107, 254, 0.3);
}

.empty-chat h2 {
  color: var(--color-text-primary);
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 6px;
}

.empty-chat p {
  color: var(--color-text-tertiary);
  font-size: 14px;
  margin-bottom: 24px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.quick-btn {
  padding: 8px 16px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: 20px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.quick-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

/* ==================== Input section ==================== */
.input-section {
  padding: 0 calc((100% - 760px) / 2) 20px;
}

.input-container {
  max-width: 760px;
  margin: 0 auto;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding: 0 2px;
}

.toolbar-select {
  width: 140px;
}

.toolbar-select :deep(.ant-select-selector) {
  font-size: 12px !important;
  color: var(--color-text-secondary) !important;
}

.toolbar-divider {
  width: 1px;
  height: 16px;
  background: var(--color-border);
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

.stream-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 10px 12px 10px 16px;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.input-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(77, 107, 254, 0.1);
}

.input-box :deep(.ant-input) {
  font-size: 14px;
  padding: 0;
  border: none !important;
  box-shadow: none !important;
  line-height: 1.6;
}

.send-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.send-btn svg {
  width: 16px;
  height: 16px;
}

.send-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-top: 6px;
  padding: 0 4px;
}
</style>
