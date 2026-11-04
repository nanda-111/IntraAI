<template>
  <div class="assistant-page">
    <aside class="session-panel">
      <div class="session-head">
        <span class="panel-label">咨询会话</span>
        <a-button size="small" type="primary" @click="createNewSession">
          <PlusOutlined /> 新会话
        </a-button>
      </div>
      <div class="session-list">
        <button
          v-for="item in sessions"
          :key="item.id"
          class="session-item"
          :class="{ active: item.id === activeId }"
          @click="selectSession(item.id)"
        >
          <div class="session-title">{{ item.title }}</div>
          <div class="session-sub">{{ item.last_message || '暂无消息' }}</div>
        </button>
        <a-empty v-if="!sessions.length" description="还没有会话" :image="simpleImage" />
      </div>
    </aside>

    <section class="conversation">
      <header class="conv-head">
        <div class="conv-model">
          <PrinterOutlined />
          <span v-if="sessionModel">{{ sessionModel.name }}</span>
          <span v-else>尚未绑定型号</span>
          <a-tag v-if="sessionModel" :color="sessionModel.support_status === 'active' ? 'green' : 'orange'">
            {{ sessionModel.support_status_label }}
          </a-tag>
        </div>
        <div class="conv-actions">
          <ModelSelect v-model="newModelId" placeholder="新会话型号" style="width: 320px" />
          <a-button size="small" :disabled="!activeId" @click="removeSession">
            <DeleteOutlined />
          </a-button>
        </div>
      </header>

      <div ref="scrollRef" class="messages">
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-icon"><MessageOutlined /></div>
          <h2>描述你的打印机问题</h2>
          <p class="muted">
            我会先确认型号，再检索当前型号已审核的官方资料。涉及拆机、电源和电路板的请求会被拒绝并建议转人工。
          </p>
          <div class="suggestions">
            <button v-for="q in suggestions" :key="q" class="suggestion" @click="send(q)">
              {{ q }}
            </button>
          </div>
        </div>

        <div v-for="(item, index) in messages" :key="index" class="msg" :class="item.role">
          <div v-if="item.role === 'assistant'" class="msg-avatar"><RobotOutlined /></div>
          <div class="msg-body">
            <div class="bubble" :class="item.role">
              <span v-if="item.streaming && !item.content" class="typing">正在检索适用资料…</span>
              <template v-else-if="item.role === 'assistant'">
                <div class="markdown" v-html="renderMarkdown(item.content)" />
                <span v-if="item.streaming" class="cursor">▍</span>
              </template>
              <span v-else class="content">{{ item.content }}</span>
            </div>
            <SourceList v-if="item.sources?.length" :sources="item.sources" class="msg-sources" />
            <div v-if="item.role === 'assistant' && !item.streaming && item.content" class="msg-foot">
              <a-button size="small" type="text" @click="feedback(item, true)">有帮助</a-button>
              <a-button size="small" type="text" @click="feedback(item, false)">未解决</a-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="showEscalation" class="escalation">
        <span>资料不足或问题未解决？</span>
        <a-button size="small" @click="$router.push('/diagnosis')">进入结构化诊断</a-button>
        <a-button size="small" type="primary" ghost @click="$router.push('/tickets')">提交工单</a-button>
      </div>

      <footer class="composer">
        <a-textarea
          v-model:value="draft"
          :auto-size="{ minRows: 1, maxRows: 4 }"
          placeholder="描述故障现象、错误码或灯态（Enter 发送，Shift+Enter 换行）"
          :disabled="sending"
          @press-enter="handleEnter"
        />
        <a-button type="primary" :loading="sending" :disabled="!draft.trim()" @click="send()">
          <SendOutlined />
        </a-button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { useRoute } from 'vue-router'
import {
  DeleteOutlined,
  MessageOutlined,
  PlusOutlined,
  PrinterOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons-vue'
import ModelSelect from '../../components/ModelSelect.vue'
import SourceList from '../../components/SourceList.vue'
import {
  createSession,
  deleteSession,
  getSession,
  getSuggestions,
  listSessions,
  streamMessage,
  submitFeedback,
} from '../../api/assistant'

const route = useRoute()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })
const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const sessions = ref([])
const activeId = ref(null)
const messages = ref([])
const sessionModel = ref(null)
const suggestions = ref([])
const newModelId = ref('')
const draft = ref('')
const sending = ref(false)
const scrollRef = ref(null)
let controller = null

const showEscalation = computed(() => {
  const last = messages.value[messages.value.length - 1]
  return (
    last?.role === 'assistant' &&
    !last.streaming &&
    !last.sources?.length &&
    last.intent !== 'safety_refusal'
  )
})

function scrollBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

function renderMarkdown(text) {
  return DOMPurify.sanitize(md.render(text || ''))
}

async function loadSessions() {
  const res = await listSessions()
  sessions.value = res.data
}

async function selectSession(id) {
  activeId.value = id
  const res = await getSession(id)
  sessionModel.value = res.data.model
  messages.value = res.data.messages.map((item) => ({ ...item, streaming: false }))
  scrollBottom()
}

async function createNewSession() {
  try {
    const payload = newModelId.value ? { model_id: newModelId.value } : {}
    const res = await createSession(payload)
    await loadSessions()
    await selectSession(res.data.id)
  } catch (err) {
    message.error(err.response?.data?.detail || '创建会话失败')
  }
}

async function removeSession() {
  if (!activeId.value) return
  await deleteSession(activeId.value)
  activeId.value = null
  messages.value = []
  sessionModel.value = null
  await loadSessions()
  if (sessions.value.length) await selectSession(sessions.value[0].id)
}

function handleEnter(event) {
  if (event.shiftKey) return
  event.preventDefault()
  send()
}

function send(text) {
  const content = (text ?? draft.value).trim()
  if (!content || sending.value || !activeId.value) return
  draft.value = ''
  sending.value = true
  messages.value.push({ role: 'user', content })
  const assistant = { role: 'assistant', content: '', sources: [], streaming: true, intent: null }
  messages.value.push(assistant)
  scrollBottom()

  controller = streamMessage(activeId.value, content, (event) => {
    if (event.type === 'meta') {
      assistant.sources = event.sources || []
      assistant.intent = event.intent
    } else if (event.type === 'answer') {
      assistant.content += event.content || ''
    } else if (event.type === 'reasoning') {
      // 不展示内部推理链
    } else if (event.type === 'error') {
      assistant.content = event.content || '服务暂时不可用，请稍后重试。'
      assistant.streaming = false
      sending.value = false
    } else if (event.type === 'done') {
      assistant.streaming = false
      sending.value = false
      loadSessions()
    }
    scrollBottom()
  })
  // 网络中断兜底
  setTimeout(() => {
    if (sending.value && assistant.streaming) {
      assistant.streaming = false
      sending.value = false
    }
  }, 90000)
}

async function feedback(item, resolved) {
  try {
    await submitFeedback({
      channel: 'assistant',
      reference_id: activeId.value,
      rating: resolved ? 5 : 2,
      resolved,
      comment: resolved ? '回答有帮助' : '问题未解决',
    })
    message.success('感谢反馈')
  } catch {
    message.error('反馈提交失败')
  }
}

onMounted(async () => {
  await loadSessions()
  const requested = Number(route.query.session)
  if (requested && sessions.value.some((item) => item.id === requested)) {
    await selectSession(requested)
  } else if (sessions.value.length) {
    await selectSession(sessions.value[0].id)
  } else {
    await createNewSession()
  }
  getSuggestions(sessionModel.value?.model_id)
    .then((res) => {
      suggestions.value = res.data.items.slice(0, 4)
    })
    .catch(() => {})
  if (route.query.q) {
    send(String(route.query.q))
  }
})

onBeforeUnmount(() => {
  if (controller) controller.abort()
})
</script>

<style scoped>
.assistant-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.session-panel {
  width: 238px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  display: flex;
  flex-direction: column;
}
.session-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 14px;
  border-bottom: 1px solid var(--color-border-light);
}
.panel-label {
  font-size: 13px;
  font-weight: 650;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.session-item:hover,
.session-item.active {
  background: var(--color-primary-bg);
}
.session-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-sub {
  font-size: 11.5px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conversation {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}
.conv-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  background: var(--color-bg-elevated);
  border-bottom: 1px solid var(--color-border-light);
}
.conv-model {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
}
.conv-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.welcome {
  max-width: 620px;
  margin: 40px auto;
  text-align: center;
}
.welcome-icon {
  width: 54px;
  height: 54px;
  margin: 0 auto 12px;
  border-radius: 16px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}
.welcome h2 {
  font-size: 20px;
  margin-bottom: 6px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}
.suggestion {
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.suggestion:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.msg {
  display: flex;
  gap: 10px;
  max-width: 900px;
}
.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.msg-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.bubble {
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}
.bubble.assistant {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
}
.bubble.user {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-sources {
  max-width: 760px;
}
.msg-foot {
  display: flex;
  gap: 4px;
}
.typing {
  color: var(--color-text-tertiary);
}
.markdown :deep(p) {
  margin: 0 0 8px;
}
.markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 4px 0 8px;
  padding-left: 20px;
}
.markdown :deep(code) {
  background: var(--color-bg-sunken);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 12px;
}
.markdown :deep(a) {
  color: var(--color-primary);
}
.cursor {
  color: var(--color-primary);
  animation: blink 1s infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}
.escalation {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 20px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  background: #fffbeb;
  border-top: 1px solid #fde68a;
}
.composer {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 14px 20px 18px;
  background: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border-light);
}
.composer :deep(textarea) {
  font-size: 13.5px;
}
</style>