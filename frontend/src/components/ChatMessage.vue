<template>
  <div :class="['message', message.role]">
    <div
      v-if="message.role === 'assistant'"
      class="avatar"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z" />
        <path d="M9 14h6" />
        <circle
          cx="9"
          cy="9"
          r="0.5"
          fill="currentColor"
        />
        <circle
          cx="15"
          cy="9"
          r="0.5"
          fill="currentColor"
        />
      </svg>
    </div>

    <div class="message-body">
      <div
        v-if="message.role === 'user'"
        class="user-bubble"
      >
        {{ message.content }}
      </div>

      <template v-else>
        <!-- Thinking indicator -->
        <div
          v-if="message.streaming && !hasReasoning"
          class="thinking-panel"
        >
          <div class="thinking-header">
            <span class="thinking-spinner" />
            <span class="thinking-label">正在思考</span>
            <span
              :ref="el => { if (el) timerEl = el }"
              class="thinking-elapsed"
            />
          </div>
        </div>

        <!-- Reasoning block -->
        <div
          v-if="hasReasoning"
          class="thinking-panel"
        >
          <div
            class="thinking-header"
            @click="toggleThinking"
          >
            <svg
              :class="['thinking-chevron', { open: showThinking }]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
            <span class="thinking-label">
              深度思考 · {{ message.reasoning_time || 0 }}s
            </span>
          </div>
          <Transition name="expand">
            <div
              v-show="showThinking"
              class="thinking-content"
            >
              {{ message.reasoning }}
            </div>
          </Transition>
        </div>

        <!-- Answer -->
        <div
          v-if="(!hasReasoning && !message.streaming) || (hasReasoning && message.reasoning_done)"
          class="answer-content"
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

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

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
  margin-bottom: 20px;
  padding: 4px 0;
}

.message.user {
  justify-content: flex-end;
}

/* User bubble */
.user-bubble {
  max-width: 70%;
  font-size: 14px;
  line-height: 1.7;
  color: #fff;
  background: var(--color-primary);
  padding: 10px 16px;
  border-radius: var(--radius-lg) var(--radius-lg) 4px var(--radius-lg);
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: var(--shadow-sm);
}

/* AI avatar */
.avatar {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary), #7c5cfc);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.avatar svg {
  width: 18px;
  height: 18px;
}

.message-body {
  flex: 1;
  max-width: 75%;
  min-width: 0;
}

/* Thinking panel */
.thinking-panel {
  margin-bottom: 10px;
  background: var(--color-bg-sunken);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 500;
  padding: 8px 12px;
  user-select: none;
  transition: color var(--transition-fast);
}

.thinking-header:hover {
  color: var(--color-text-primary);
}

.thinking-chevron {
  width: 14px;
  height: 14px;
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}

.thinking-chevron.open {
  transform: rotate(90deg);
}

.thinking-elapsed {
  margin-left: auto;
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-variant-numeric: tabular-nums;
}

.thinking-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.thinking-content {
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.7;
  padding: 0 12px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
}

/* Answer content */
.answer-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-primary);
}

.answer-content :deep(pre) {
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: var(--radius-md);
  padding: 14px 16px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
}

.answer-content :deep(code) {
  font-family: var(--font-mono);
  font-size: 13px;
}

.answer-content :deep(p code) {
  background: var(--color-bg-sunken);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.answer-content :deep(p) {
  margin: 0 0 8px;
}

.answer-content :deep(p:last-child) {
  margin-bottom: 0;
}

.answer-content :deep(ul),
.answer-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0 8px;
}

.answer-content :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 12px;
  color: var(--color-text-secondary);
  margin: 8px 0;
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
