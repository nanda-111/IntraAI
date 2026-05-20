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
