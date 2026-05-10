<!-- 管理后台页面占位组件 -->
<!-- 提供导航栏和空状态提示，完整功能将在阶段 5 实现 -->
<template>
  <a-layout>
    <!-- 页面顶部导航栏 -->
    <a-layout-header class="header">
      <!-- 应用 Logo -->
      <div class="logo">IntraAI</div>
      <!-- 水平导航菜单，默认选中"管理"项 -->
      <a-menu theme="dark" mode="horizontal" :selected-keys="['admin']">
        <a-menu-item key="chat" @click="$router.push('/')">对话</a-menu-item>
        <a-menu-item key="knowledge" @click="$router.push('/knowledge')">知识库</a-menu-item>
        <a-menu-item key="admin">管理</a-menu-item>
      </a-menu>
      <!-- 退出登录按钮 -->
      <a-button type="text" style="color: white" @click="handleLogout">退出</a-button>
    </a-layout-header>
    <!-- 页面主内容区域 -->
    <a-layout-content style="padding: 24px; display: flex; justify-content: center; align-items: center;">
      <!-- 空状态提示：管理后台功能尚未实现 -->
      <a-empty description="管理后台将在阶段 5 实现" />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// 路由实例
const router = useRouter()
// 认证状态管理
const authStore = useAuthStore()

/**
 * 处理退出登录
 * 清除认证信息并跳转到登录页
 */
function handleLogout() {
  authStore.logout()
  router.push('/login')
}
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
</style>
