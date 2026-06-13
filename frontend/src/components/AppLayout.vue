<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">
          IntraAI
        </div>
        <!-- 各页面自定义的侧边栏内容（如 ChatView 的新建按钮和会话列表） -->
        <slot name="sidebar-extra" />
      </div>
      <div class="sidebar-bottom">
        <div class="nav-links">
          <router-link
            to="/"
            :class="['nav-link', { active: activeRoute === '/' }]"
          >
            对话
          </router-link>
          <router-link
            to="/knowledge"
            :class="['nav-link', { active: activeRoute === '/knowledge' }]"
          >
            知识库
          </router-link>
          <router-link
            v-if="isAdmin"
            to="/admin"
            :class="['nav-link', { active: activeRoute === '/admin' }]"
          >
            管理
          </router-link>
        </div>
        <button
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </aside>

    <main :class="mainClass">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

defineProps({
  /** 主内容区的额外 CSS 类名 */
  mainClass: {
    type: String,
    default: 'main-content',
  },
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isAdmin = computed(() => authStore.user?.is_admin)
const activeRoute = computed(() => route.path)

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
}

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
</style>
