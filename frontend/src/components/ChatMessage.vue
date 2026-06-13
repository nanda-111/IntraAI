<template>
  <div :class="['message', message.role]">
    <div
      v-if="message.role === 'assistant'"
      class="avatar"
    >
      AI
    </div>

    <div class="message-body">
      <div
        v-if="message.role === 'user'"
        class="user-content"
      >
        {{ message.content }}
      </div>

      <template v-else>
        <!-- 思考中状态：reasoning 为 null 且仍在流式 -->
        <div
          v-if="message.streaming && !hasReasoning"
          class="thinking-panel"
        >
          <div class="thinking-header">
            <span class="thinking-spinner" />
            <span class="thinking-label">思考中...</span>
            <span
              :ref="el => { if (el) timerEl = el }"
              class="thinking-elapsed"
            />
          </div>
        </div>

        <!-- 思考完成：有 reasoning 内容 -->
        <div
          v-if="hasReasoning"
          class="thinking-panel"
        >
          <div
            class="thinking-header"
            @click="toggleThinking"
          >
            <span class="thinking-arrow">{{ showThinking ? '▾' : '▸' }}</span>
            <span class="thinking-label">
              已思考 {{ message.reasoning_time || 0 }} 秒
            </span>
          </div>
          <div
            v-show="showThinking"
            class="thinking-content"
          >
            {{ message.reasoning }}
          </div>
        </div>

        <!-- 回答：无 reasoning 且非流式中，或有 reasoning 且已完成 -->
        <div
          v-if="(!hasReasoning && !message.streaming) || (hasReasoning && message.reasoning_done)"
          class="content"
          v-html="renderedContent"
        />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const md = new MarkdownIt()

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const showThinking = ref(false)
let timerEl = null
let timerInterval = null
let timerStart = null

const hasReasoning = computed(() => props.message.reasoning != null)

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    const raw = md.render(props.message.content || '')
    return DOMPurify.sanitize(raw)
  }
  return props.message.content
})

// 用原生 DOM 操作更新计时器，完全绕过 Vue 响应式系统
watch(
  () => props.message.streaming,
  (streaming) => {
    if (streaming) {
      timerStart = Date.now()
      clearInterval(timerInterval)
      timerInterval = setInterval(() => {
        if (timerEl) {
          const sec = Math.round((Date.now() - timerStart) / 1000)
          timerEl.textContent = ` ${sec}s`
        }
      }, 1000)
    } else {
      clearInterval(timerInterval)
      timerInterval = null
    }
  },
  { immediate: true }
)

onUnmounted(() => clearInterval(timerInterval))

function toggleThinking() {
  showThinking.value = !showThinking.value
}
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  padding: 8px 0;
}

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

.thinking-elapsed {
  font-size: 12px;
  color: #aaa;
}

.thinking-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #ddd;
  border-top-color: #4D6BFE;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
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

.content {
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a2e;
}

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
