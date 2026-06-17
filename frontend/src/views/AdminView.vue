<template>
  <AppLayout main-class="main-content-admin">
    <a-layout>
      <a-layout-sider
        width="200"
        theme="light"
      >
        <a-menu
          v-model:selected-keys="activeTab"
          mode="inline"
          style="height: 100%"
        >
          <a-menu-item key="stats">
            数据概览
          </a-menu-item>
          <a-menu-item key="users">
            用户管理
          </a-menu-item>
          <a-menu-item key="kbs">
            知识库管理
          </a-menu-item>
          <a-menu-item key="logs">
            操作日志
          </a-menu-item>
        </a-menu>
      </a-layout-sider>

      <a-layout-content class="admin-content">
        <!-- Stats -->
        <template v-if="activeTab[0] === 'stats'">
          <div class="page-header">
            <h2 class="page-title">
              数据概览
            </h2>
            <p class="page-subtitle">
              平台运行状态一览
            </p>
          </div>
          <a-row :gutter="[16, 16]">
            <a-col
              v-for="item in statCards"
              :key="item.title"
              :xs="24"
              :sm="12"
              :lg="6"
            >
              <div class="stat-card">
                <div class="stat-icon">
                  <component :is="item.icon" />
                </div>
                <div class="stat-info">
                  <span class="stat-value">{{ item.value }}</span>
                  <span class="stat-label">{{ item.title }}</span>
                </div>
              </div>
            </a-col>
          </a-row>
        </template>

        <!-- Users -->
        <template v-if="activeTab[0] === 'users'">
          <div class="page-header">
            <h2 class="page-title">
              用户管理
            </h2>
            <p class="page-subtitle">
              管理平台用户账号和权限
            </p>
          </div>
          <a-card>
            <a-table
              :data-source="users"
              :columns="userColumns"
              row-key="id"
              :loading="loadingUsers"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.is_active ? 'green' : 'red'">
                    {{ record.is_active ? '正常' : '禁用' }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'admin'">
                  <a-tag :color="record.is_admin ? 'blue' : 'default'">
                    {{ record.is_admin ? '管理员' : '用户' }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'action'">
                  <a-space>
                    <a-button
                      size="small"
                      @click="handleToggleUser(record)"
                    >
                      {{ record.is_active ? '禁用' : '启用' }}
                    </a-button>
                    <a-button
                      size="small"
                      @click="handleToggleAdmin(record)"
                    >
                      {{ record.is_admin ? '取消管理员' : '设为管理员' }}
                    </a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </a-card>
        </template>

        <!-- KBs -->
        <template v-if="activeTab[0] === 'kbs'">
          <div class="page-header">
            <h2 class="page-title">
              知识库管理
            </h2>
            <p class="page-subtitle">
              查看所有知识库信息
            </p>
          </div>
          <a-card>
            <a-table
              :data-source="adminKbs"
              :columns="kbColumns"
              row-key="id"
              :loading="loadingKbs"
            />
          </a-card>
        </template>

        <!-- Logs -->
        <template v-if="activeTab[0] === 'logs'">
          <div class="page-header">
            <h2 class="page-title">
              操作日志
            </h2>
            <p class="page-subtitle">
              用户操作记录审计
            </p>
          </div>
          <a-card>
            <a-table
              :data-source="logs"
              :columns="logColumns"
              row-key="id"
              :loading="loadingLogs"
              :pagination="{ current: logPage, total: logTotal, pageSize: 20, onChange: handleLogPageChange }"
            />
          </a-card>
        </template>
      </a-layout-content>
    </a-layout>
  </AppLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted, h } from 'vue'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'
import {
  getStats,
  getUsers,
  toggleUser,
  toggleAdmin,
  getAdminKnowledgeBases,
  getUsageLogs
} from '../api/admin'

const authStore = useAuthStore()
const activeTab = ref(['stats'])

// Stats
const stats = ref({})

// SVG icon components for stat cards
const UserIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', style: 'width:20px;height:20px' }, [
    h('path', { d: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2' }),
    h('circle', { cx: '9', cy: '7', r: '4' }),
    h('path', { d: 'M23 21v-2a4 4 0 0 0-3-3.87' }),
    h('path', { d: 'M16 3.13a4 4 0 0 1 0 7.75' }),
  ]),
}

const ActiveIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', style: 'width:20px;height:20px' }, [
    h('path', { d: 'M22 11.08V12a10 10 0 1 1-5.93-9.14' }),
    h('polyline', { points: '22 4 12 14.01 9 11.01' }),
  ]),
}

const KbIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', style: 'width:20px;height:20px' }, [
    h('path', { d: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20' }),
    h('path', { d: 'M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z' }),
  ]),
}

const ChatIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', style: 'width:20px;height:20px' }, [
    h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' }),
  ]),
}

const statCards = computed(() => [
  { title: '总用户数', value: stats.value.user_count || 0, icon: UserIcon, color: '#4D6BFE' },
  { title: '活跃用户', value: stats.value.active_user_count || 0, icon: ActiveIcon, color: '#22c55e' },
  { title: '知识库数', value: stats.value.kb_count || 0, icon: KbIcon, color: '#f59e0b' },
  { title: '对话次数', value: stats.value.chat_count || 0, icon: ChatIcon, color: '#8b5cf6' },
])

// Users
const users = ref([])
const loadingUsers = ref(false)
const userColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户名', dataIndex: 'username' },
  { title: '邮箱', dataIndex: 'email' },
  { title: '状态', key: 'status' },
  { title: '角色', key: 'admin' },
  { title: '注册时间', dataIndex: 'created_at' },
  { title: '操作', key: 'action', width: 250 },
]

// KBs
const adminKbs = ref([])
const loadingKbs = ref(false)
const kbColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '名称', dataIndex: 'name' },
  { title: '描述', dataIndex: 'description' },
  { title: '所有者', dataIndex: 'owner' },
  { title: '文档数', dataIndex: 'doc_count' },
  { title: '创建时间', dataIndex: 'created_at' },
]

// Logs
const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const loadingLogs = ref(false)
const logColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户', dataIndex: 'user' },
  { title: '操作', dataIndex: 'action' },
  { title: '时间', dataIndex: 'created_at' },
]

async function fetchStats() {
  const res = await getStats()
  stats.value = res.data
}

async function fetchUsers() {
  loadingUsers.value = true
  try {
    const res = await getUsers()
    users.value = res.data
  } finally {
    loadingUsers.value = false
  }
}

async function fetchKbs() {
  loadingKbs.value = true
  try {
    const res = await getAdminKnowledgeBases()
    adminKbs.value = res.data
  } finally {
    loadingKbs.value = false
  }
}

async function fetchLogs(page = 1) {
  loadingLogs.value = true
  try {
    const res = await getUsageLogs({ page, size: 20 })
    logs.value = res.data.items
    logTotal.value = res.data.total
    logPage.value = page
  } finally {
    loadingLogs.value = false
  }
}

async function handleToggleUser(record) {
  await toggleUser(record.id)
  message.success('操作成功')
  fetchUsers()
}

async function handleToggleAdmin(record) {
  await toggleAdmin(record.id)
  message.success('操作成功')
  fetchUsers()
}

function handleLogPageChange(page) {
  fetchLogs(page)
}

watch(activeTab, ([tab]) => {
  if (tab === 'stats') fetchStats()
  if (tab === 'users') fetchUsers()
  if (tab === 'kbs') fetchKbs()
  if (tab === 'logs') fetchLogs()
})

onMounted(() => {
  authStore.fetchUser()
  fetchStats()
})
</script>

<style scoped>
.main-content-admin {
  flex: 1;
  display: flex;
  background: var(--color-bg);
  overflow: hidden;
}

.admin-content {
  padding: 28px 32px;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 0;
}

/* Stat cards */
.stat-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: box-shadow var(--transition-normal);
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}
</style>
