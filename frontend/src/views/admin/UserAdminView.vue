<template>
  <div class="page">
    <PageHeader title="用户与权限" subtitle="RBAC 角色：普通用户、客服人员、知识库管理员、系统管理员。关键操作会写入审计日志。">
      <template #actions>
        <a-button @click="load"><ReloadOutlined /> 刷新</a-button>
      </template>
    </PageHeader>

    <a-tabs v-model:activeKey="tab">
      <a-tab-pane key="users" tab="用户列表">
        <a-spin :spinning="loading">
          <a-table :data-source="users" :columns="userColumns" :pagination="{ pageSize: 10 }" row-key="id" size="middle">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'user'">
                <div class="name-cell">{{ record.display_name || record.username }}</div>
                <div class="tiny">{{ record.username }} · {{ record.email }}</div>
              </template>
              <template v-else-if="column.key === 'role'">
                <a-select
                  :value="record.role || (record.is_admin ? 'system_admin' : 'user')"
                  size="small"
                  style="width: 130px"
                  :disabled="record.id === auth.user?.id"
                  @change="(value) => changeRole(record, value)"
                >
                  <a-select-option value="user">普通用户</a-select-option>
                  <a-select-option value="agent">客服人员</a-select-option>
                  <a-select-option value="knowledge_admin">知识库管理员</a-select-option>
                  <a-select-option value="system_admin">系统管理员</a-select-option>
                </a-select>
              </template>
              <template v-else-if="column.key === 'active'">
                <a-switch
                  :checked="record.is_active"
                  :disabled="record.id === auth.user?.id"
                  @change="() => toggleActive(record)"
                />
              </template>
              <template v-else-if="column.key === 'time'">{{ formatTime(record.created_at) }}</template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>

      <a-tab-pane key="audit" tab="审计日志">
        <div class="filter-bar" style="margin-bottom: 14px">
          <a-input-search v-model:value="auditAction" placeholder="按操作筛选，如 knowledge.publish" style="width: 300px" @search="loadAudit" />
        </div>
        <a-spin :spinning="auditLoading">
          <a-table :data-source="auditLogs" :columns="auditColumns" :pagination="{ pageSize: 15 }" row-key="id" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'time'">{{ formatTime(record.created_at) }}</template>
              <template v-else-if="column.key === 'target'">
                {{ record.target_type || '—' }} <span class="tiny">{{ record.target_id || '' }}</span>
              </template>
              <template v-else-if="column.key === 'change'">
                <span class="tiny">{{ record.before_value || '—' }} → {{ record.after_value || '—' }}</span>
              </template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { getAuditLogs, getUsers, setUserRole, toggleUserActive } from '../../api/overview'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const tab = ref('users')
const users = ref([])
const loading = ref(false)
const auditLogs = ref([])
const auditAction = ref('')
const auditLoading = ref(false)

const userColumns = [
  { title: '用户', key: 'user', dataIndex: 'username' },
  { title: '角色', key: 'role', width: 160 },
  { title: '账号状态', key: 'active', width: 100 },
  { title: '注册时间', key: 'time', width: 180 },
]
const auditColumns = [
  { title: '时间', key: 'time', width: 180 },
  { title: '操作人', dataIndex: 'operator', width: 110 },
  { title: '操作', dataIndex: 'action', width: 180 },
  { title: '对象', key: 'target', width: 180 },
  { title: '变更', key: 'change' },
  { title: '原因', dataIndex: 'reason', width: 180 },
]

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

async function load() {
  loading.value = true
  try {
    const res = await getUsers()
    users.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadAudit() {
  auditLoading.value = true
  try {
    const params = { size: 50 }
    if (auditAction.value) params.action = auditAction.value
    const res = await getAuditLogs(params)
    auditLogs.value = res.data.items
  } finally {
    auditLoading.value = false
  }
}

async function changeRole(record, role) {
  try {
    await setUserRole(record.id, role)
    message.success('角色已更新')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '更新失败')
  }
}

async function toggleActive(record) {
  try {
    await toggleUserActive(record.id)
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(async () => {
  await Promise.all([load(), loadAudit()])
})
</script>

<style scoped>
.name-cell {
  font-weight: 600;
}
</style>