<!--
  ChatMessage 聊天气泡组件

  功能：展示一条聊天消息，支持用户消息和 AI 助手消息两种样式。
  - 用户消息：蓝色背景，靠右显示
  - AI 消息：灰色背景，靠左显示，支持 Markdown 渲染
-->
<template>
  <!-- 消息容器：根据 role 类型（user/assistant）添加对应 CSS 类名 -->
  <div :class="['message', message.role]">
    <!-- 头像区域：显示"我"或"AI"标识 -->
    <div class="avatar">
      {{ message.role === 'user' ? '我' : 'AI' }}
    </div>
    <!-- 消息内容区域 -->
    <!--
      【v-html 的安全风险与安全使用场景】

      v-html 会将字符串作为 HTML 直接插入 DOM，存在 XSS（跨站脚本攻击）风险：
      - 如果恶意用户在消息内容中注入 <script>alert('xss')</script> 等恶意代码，
        浏览器会直接执行这段脚本，可能导致用户信息泄露或页面被篡改。

      这里可以安全使用 v-html 的原因：
      1. 用户的消息（role='user'）不经过 v-html 渲染，而是作为纯文本显示（通过 computed 判断）。
      2. AI 的回答（role='assistant'）由后端返回，内容来源于可信的 AI 模型，
         不是由其他用户直接输入的，且经过 markdown-it 渲染为 HTML。
      3. 如果需要更严格的防护，可以对 markdown-it 配置 html: true 选项来过滤原始 HTML 标签，
         或使用 DOMPurify 库对输出的 HTML 进行消毒处理。
    -->
    <div class="content" v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
// markdown-it 是一个将 Markdown 文本转换为 HTML 的 JavaScript 库
// 它支持标准 Markdown 语法（标题、列表、代码块、链接、加粗、斜体等）
// 使用方式：调用 md.render(markdownText) 即可得到对应的 HTML 字符串
import MarkdownIt from 'markdown-it'

// 创建 markdown-it 实例
// 这里使用默认配置，如需自定义可通过参数调整，例如：
// const md = new MarkdownIt({ html: true, linkify: true, typographer: true })
const md = new MarkdownIt()

// 定义组件接收的 props
// message 对象包含两个字段：
//   - role: 'user' | 'assistant'，标识消息发送者
//   - content: 消息的文本内容
const props = defineProps({
  message: Object,
})

/**
 * 【computed 计算属性的响应式机制】
 *
 * computed 会创建一个响应式计算属性，其工作机制如下：
 * 1. 首次访问时，computed 执行内部函数并缓存返回值。
 * 2. 当其依赖的响应式数据（这里指 props.message）发生变化时，
 *    Vue 的响应式系统会自动检测到依赖变化，标记该 computed 为"需要重新计算"。
 * 3. 下次访问时，computed 会重新执行函数并返回新结果，同时更新缓存。
 * 4. 如果依赖没有变化，computed 直接返回缓存值，避免重复计算，提高性能。
 *
 * 这里 computed 依赖 props.message，当消息内容或角色变化时，
 * renderedContent 会自动重新计算，触发视图更新。
 */
const renderedContent = computed(() => {
  // AI 助手的消息使用 markdown-it 渲染为 HTML
  // 支持代码高亮、列表、标题等丰富的 Markdown 格式展示
  if (props.message.role === 'assistant') {
    return md.render(props.message.content)
  }
  // 用户的消息保持纯文本，直接返回不做 Markdown 渲染
  return props.message.content
})
</script>

<style scoped>
/* 消息容器：水平排列头像和内容 */
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 8px 0;
}
/* 用户消息反向排列（头像在右，内容在左），实现靠右显示效果 */
.message.user {
  flex-direction: row-reverse;
}
/* 头像样式：圆形，固定尺寸 */
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0; /* 防止头像被压缩 */
}
/* 用户头像：蓝色背景 */
.message.user .avatar {
  background: #1677ff;
  color: white;
}
/* AI 头像：绿色背景 */
.message.assistant .avatar {
  background: #52c41a;
  color: white;
}
/* 消息气泡样式 */
.content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
}
/* 用户消息气泡：蓝色背景，白色文字 */
.message.user .content {
  background: #1677ff;
  color: white;
}
/* AI 消息气泡：浅灰色背景 */
.message.assistant .content {
  background: #f5f5f5;
}
</style>
