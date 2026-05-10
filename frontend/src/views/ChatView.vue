<!--
  ChatView 对话页面

  功能：实现完整的 AI 对话界面，包括：
  - 顶部导航栏（含对话/知识库/管理员菜单和退出按钮）
  - 消息列表区域（自动滚动到最新消息）
  - 知识库选择器（可选，选择后 AI 基于该知识库回答）
  - 问题输入框和发送按钮
-->
<template>
  <a-layout style="height: 100vh">
    <!-- 顶部导航栏 -->
    <a-layout-header class="header">
      <!-- 应用 Logo -->
      <div class="logo">IntraAI</div>
      <!-- 水平导航菜单，默认选中"对话"项 -->
      <a-menu theme="dark" mode="horizontal" :selected-keys="['chat']">
        <a-menu-item key="chat">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <!-- 仅管理员可见的管理菜单项 -->
        <a-menu-item key="admin" v-if="authStore.user?.is_admin" @click="$router.push('/admin')">管理</a-menu-item>
      </a-menu>
      <!-- 退出登录按钮 -->
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>

    <!-- 主内容区：居中显示对话区域 -->
    <a-layout-content class="chat-content">
      <div class="chat-area">
        <!-- 消息列表区域 -->
        <!--
          【ref 引用和 scrollToBottom 的实现】

          Vue 3 中 ref 可以用于获取 DOM 元素的引用：
          - 在模板中通过 ref="messagesRef" 将 DOM 元素绑定到 messagesRef 变量
          - 在 JavaScript 中通过 messagesRef.value 访问实际的 DOM 元素
          - 注意：DOM 元素在组件挂载后（onMounted）才可用，在此之前 messagesRef.value 为 null

          scrollToBottom 实现自动滚动到底部：
          - scrollHeight：元素内容的总高度（包括溢出不可见的部分）
          - scrollTop：元素当前滚动的位置（距顶部的距离）
          - 将 scrollTop 设为 scrollHeight，即可滚动到最底部，展示最新消息
        -->
        <div class="messages" ref="messagesRef">
          <!-- 没有消息时显示空状态提示 -->
          <a-empty v-if="messages.length === 0" description="选择知识库后开始提问" />
          <!-- 遍历消息列表，每条消息用 ChatMessage 组件渲染 -->
          <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <!-- 知识库选择器：可选，选择后 AI 会基于该知识库内容回答问题 -->
          <a-select
            v-model:value="selectedKb"
            placeholder="选择知识库（可选）"
            style="width: 200px; margin-bottom: 8px"
            :options="kbOptions"
            allow-clear
          />
          <!-- 输入框 + 发送按钮 -->
          <div class="input-row">
            <!-- 多行文本输入框，自适应高度（最小1行，最大4行） -->
            <a-textarea
              v-model:value="question"
              placeholder="输入问题..."
              :auto-size="{ minRows: 1, maxRows: 4 }"
              @keydown.enter.exact="handleSend"
            />
            <!-- 发送按钮，加载中时显示 loading 状态 -->
            <a-button type="primary" :loading="loading" @click="handleSend">发送</a-button>
          </div>
        </div>
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases } from '../api/knowledge'
import { sendChat } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'

// 路由实例
const router = useRouter()
// 认证状态管理
const authStore = useAuthStore()

// 消息列表：每条消息包含 role（user/assistant）和 content 字段
const messages = ref([])
// 用户当前输入的问题文本
const question = ref('')
// 请求加载状态，防止重复发送
const loading = ref(false)

// 当前选中的知识库 ID（可为 null，表示不指定知识库）
const selectedKb = ref(null)
// 知识库下拉选项列表
const kbOptions = ref([])

/**
 * 【ref 引用】
 *
 * messagesRef 是一个 ref 引用，指向消息列表的 DOM 容器元素。
 * 在模板中通过 ref="messagesRef" 属性将 DOM 元素绑定到此 ref。
 * 使用 messagesRef.value 可以访问该 DOM 元素，进而操作其属性和方法。
 */
const messagesRef = ref(null)

/**
 * 获取知识库列表
 * 将后端返回的知识库数据转换为下拉选择器所需的 options 格式
 * 格式：[{ label: '知识库名称', value: 知识库ID }, ...]
 */
async function fetchKbs() {
  const res = await listKnowledgeBases()
  kbOptions.value = res.data.map(kb => ({ label: kb.name, value: kb.id }))
}

/**
 * 发送消息
 *
 * 处理流程：
 * 1. 校验输入不为空且未处于加载状态
 * 2. 立即清空输入框（提升用户体验）
 * 3. 将用户消息添加到消息列表
 * 4. 调用后端 API 获取 AI 回答
 * 5. 将 AI 回答添加到消息列表
 */
async function handleSend() {
  // 输入校验：空消息或正在加载时不发送
  if (!question.value.trim() || loading.value) return

  // 保存问题内容并立即清空输入框
  const q = question.value.trim()
  question.value = ''

  // 将用户消息添加到消息列表
  messages.value.push({ role: 'user', content: q })
  loading.value = true

  /**
   * 【nextTick 的作用】
   *
   * nextTick 用于等待 DOM 更新完成后执行回调函数。
   *
   * Vue 的响应式数据更新后，DOM 不会立即同步更新，而是放入一个异步队列中。
   * nextTick 可以确保在 DOM 确实更新完毕后再执行后续操作。
   *
   * 这里使用 nextTick 的原因：
   * - 用户消息刚添加到 messages 数组，Vue 需要时间将新消息渲染到 DOM 中
   * - 只有 DOM 中出现了新消息元素，scrollHeight 才会增大
   * - 如果不等待 DOM 更新就执行 scrollToBottom，滚动位置可能不正确
   * - 使用 nextTick 后，确保新消息已经在 DOM 中渲染完毕，再滚动到底部
   */
  await nextTick()
  // 新消息渲染到 DOM 后，滚动到消息列表底部
  scrollToBottom()

  try {
    // 调用后端对话 API，传入问题和可选的知识库 ID
    const res = await sendChat({ question: q, kb_id: selectedKb.value })
    // 将 AI 回答添加到消息列表
    messages.value.push({ role: 'assistant', content: res.data.answer })
  } catch {
    // 请求失败时显示错误提示
    message.error('发送失败')
  } finally {
    loading.value = false
    /**
     * 等待 DOM 更新后再次滚动到底部
     * 因为 AI 回答的消息刚添加到列表，需要等 DOM 渲染完成后才能正确滚动
     */
    await nextTick()
    scrollToBottom()
  }
}

/**
 * 滚动到消息列表底部
 *
 * 实现原理：
 * - messagesRef.value 是消息列表的 DOM 容器元素
 * - scrollHeight 是容器内容的总高度（包括不可见的溢出部分）
 * - 将 scrollTop 设为 scrollHeight，即可将滚动条定位到最底部
 * - 这样用户每次发送或收到消息后，都能自动看到最新的内容
 */
function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

/**
 * 处理退出登录
 * 清除认证信息并跳转到登录页
 */
function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// 页面加载时获取当前用户信息和知识库列表
onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
})
</script>

<style scoped>
/* 顶部导航栏布局：水平排列子元素 */
.header {
  display: flex;
  align-items: center;
}
/* Logo 样式 */
.logo {
  color: white;
  font-size: 18px;
  font-weight: bold;
  margin-right: 24px;
}
/* 主内容区域：居中布局，限制最大宽度 */
.chat-content {
  display: flex;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}
/* 对话区域：垂直布局，占满剩余高度 */
.chat-area {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
/* 消息列表：自适应高度，内容溢出时可滚动 */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
/* 输入区域：顶部边框分隔 */
.input-area {
  border-top: 1px solid #f0f0f0;
  padding-top: 12px;
}
/* 输入框和发送按钮：水平排列，间距 8px */
.input-row {
  display: flex;
  gap: 8px;
}
</style>
