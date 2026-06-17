<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">
          <div class="logo-icon">
            AI
          </div>
          <div class="logo-text">
            <span class="logo-name">IntraAI</span>
            <span class="logo-version">v2.5</span>
          </div>
        </div>
        <slot name="sidebar-extra" />
      </div>
      <div class="sidebar-bottom">
        <nav class="nav-links">
          <router-link
            to="/"
            :class="['nav-link', { active: activeRoute === '/' }]"
          >
            <svg
              class="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            对话
          </router-link>
          <router-link
            to="/knowledge"
            :class="['nav-link', { active: activeRoute === '/knowledge' }]"
          >
            <svg
              class="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            知识库
          </router-link>
          <router-link
            v-if="isAdmin"
            to="/admin"
            :class="['nav-link', { active: activeRoute === '/admin' }]"
          >
            <svg
              class="nav-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <rect
                x="3"
                y="3"
                width="7"
                height="7"
                rx="1"
              />
              <rect
                x="14"
                y="3"
                width="7"
                height="7"
                rx="1"
              />
              <rect
                x="3"
                y="14"
                width="7"
                height="7"
                rx="1"
              />
              <rect
                x="14"
                y="14"
                width="7"
                height="7"
                rx="1"
              />
            </svg>
            管理
          </router-link>
        </nav>
        <div class="sidebar-user">
          <div class="user-avatar">
            {{ userInitial }}
          </div>
          <div class="user-info">
            <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
            <span class="user-role">{{ isAdmin ? '管理员' : '成员' }}</span>
          </div>
          <button
            class="logout-btn"
            title="退出登录"
            @click="handleLogout"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line
                x1="21"
                y1="12"
                x2="9"
                y2="12"
              />
            </svg>
          </button>
        </div>
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
const userInitial = computed(() => {
  const name = authStore.user?.username || ''
  return name.charAt(0).toUpperCase() || 'U'
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ==================== Sidebar ==================== */
.sidebar {
  width: 260px;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 1px;
  background: var(--sidebar-border);
}

.sidebar-top {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 20px 16px;
}

/* Logo */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;
  padding: 0 4px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--color-primary), #7c5cfc);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.logo-text {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.logo-name {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.3px;
}

.logo-version {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  font-weight: 500;
}

/* Bottom section */
.sidebar-bottom {
  padding: 12px 16px 16px;
  border-top: 1px solid var(--sidebar-border);
}

/* Navigation */
.nav-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 16px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--sidebar-text);
  text-decoration: none;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  background: var(--sidebar-surface-hover);
  color: var(--sidebar-text-active);
}

.nav-link.active {
  background: var(--sidebar-surface-active);
  color: var(--sidebar-text-active);
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* User info */
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.sidebar-user:hover {
  background: var(--sidebar-surface);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--sidebar-text-active);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 11px;
  color: var(--sidebar-text);
}

.logout-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--sidebar-text);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.logout-btn svg {
  width: 16px;
  height: 16px;
}

.logout-btn:hover {
  background: var(--sidebar-surface-hover);
  color: var(--color-danger);
}

/* ==================== Main content ==================== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  overflow: hidden;
  min-width: 0;
}
</style>
