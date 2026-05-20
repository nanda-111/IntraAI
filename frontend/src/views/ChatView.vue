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
