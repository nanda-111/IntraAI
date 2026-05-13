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
