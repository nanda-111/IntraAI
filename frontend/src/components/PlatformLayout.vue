<template>
  <div class="platform">
    <aside class="side">
      <router-link to="/dashboard" class="brand">
        <div class="brand-logo"><PrinterOutlined /></div>
        <div class="brand-text">
          <span class="brand-name">PrintCare</span>
          <span class="brand-sub">打印机售后智能平台</span>
        </div>
      </router-link>

      <div class="side-scroll">
        <div v-for="group in groups" :key="group.title" class="nav-group">
          <div class="group-title">{{ group.title }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            :class="{ active: isActive(item.to) }"
          >
            <component :is="item.icon" class="nav-icon" />
            <span>{{ item.label }}</span>
          </router-link>
        </div>
      </div>

      <div class="side-user">
        <div class="avatar">{{ initial }}</div>
        <div class="user-meta">
          <span class="user-name">{{ auth.user?.display_name || auth.user?.username || '用户' }}</span>
          <span class="user-role">{{ roleLabel }}</span>
        </div>
        <a-tooltip title="退出登录">
          <button class="logout" @click="handleLogout"><LogoutOutlined /></button>
        </a-tooltip>
      </div>
    </aside>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AppstoreOutlined,
  AuditOutlined,
  BookOutlined,
  CloudUploadOutlined,
  CustomerServiceOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  HistoryOutlined,
  HomeOutlined,
  LogoutOutlined,
  MessageOutlined,
  PrinterOutlined,
  SettingOutlined,
  TeamOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const userGroup = [
  { to: '/dashboard', label: '服务首页', icon: HomeOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/products', label: '品牌与型号', icon: PrinterOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/knowledge', label: '知识中心', icon: BookOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/assistant', label: '智能客服', icon: MessageOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/diagnosis', label: '故障诊断', icon: ToolOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/maintenance', label: '维护与耗材', icon: CustomerServiceOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/history', label: '我的服务记录', icon: HistoryOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/tickets', label: '售后工单', icon: FileTextOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
  { to: '/profile', label: '个人中心', icon: UserOutlined, roles: ['user', 'agent', 'knowledge_admin', 'system_admin'] },
]

const adminGroup = [
  { to: '/admin/dashboard', label: '运营概览', icon: DashboardOutlined, roles: ['agent', 'knowledge_admin', 'system_admin'] },
  { to: '/admin/products', label: '品牌型号管理', icon: PrinterOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/knowledge/sources', label: '知识来源', icon: BookOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/knowledge/import', label: '文档导入', icon: CloudUploadOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/knowledge/review', label: '知识审核', icon: AuditOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/cases', label: '维修案例', icon: AppstoreOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/tickets', label: '工单管理', icon: FileTextOutlined, roles: ['agent', 'system_admin'] },
  { to: '/admin/evaluation', label: '评测中心', icon: ExperimentOutlined, roles: ['knowledge_admin', 'system_admin'] },
  { to: '/admin/users', label: '用户与权限', icon: TeamOutlined, roles: ['system_admin'] },
  { to: '/admin/settings', label: '系统配置', icon: SettingOutlined, roles: ['system_admin'] },
]

const groups = computed(() => {
  const role = auth.role
  const result = [
    { title: '用户服务', items: userGroup.filter((item) => item.roles.includes(role)) },
  ]
  if (role !== 'user') {
    const items = adminGroup.filter((item) => item.roles.includes(role))
    if (items.length) result.push({ title: '运营管理', items })
  }
  return result
})

const roleLabel = computed(
  () =>
    ({
      user: '普通用户',
      agent: '客服人员',
      knowledge_admin: '知识库管理员',
      system_admin: '系统管理员',
    })[auth.role] || '普通用户',
)
const initial = computed(() => (auth.user?.username || 'U').charAt(0).toUpperCase())

function isActive(path) {
  if (path === '/dashboard') return route.path === '/dashboard'
  return route.path === path || route.path.startsWith(`${path}/`)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  if (auth.token && !auth.user) auth.fetchUser().catch(() => {})
})
</script>

<style scoped>
.platform {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.side {
  width: 240px;
  flex-shrink: 0;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--sidebar-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 16px;
  text-decoration: none;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), #7c5cfc);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.3px;
}

.brand-sub {
  color: rgba(255, 255, 255, 0.38);
  font-size: 10px;
  white-space: nowrap;
}

.side-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}

.nav-group + .nav-group {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--sidebar-border);
}

.group-title {
  padding: 0 10px 6px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.28);
  text-transform: uppercase;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 13.5px;
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
  font-size: 16px;
  flex-shrink: 0;
}

.side-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--sidebar-border);
}

.avatar {
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

.user-meta {
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

.logout {
  width: 30px;
  height: 30px;
  border: none;
  background: none;
  color: var(--sidebar-text);
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.logout:hover {
  background: var(--sidebar-surface-hover);
  color: var(--color-danger);
}

.main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: var(--color-bg);
}
</style>