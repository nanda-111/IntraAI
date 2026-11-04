<template>
  <div class="page">
    <PageHeader title="售后工单管理" subtitle="筛选、分配、处理、备注和关闭工单；可查看用户授权的诊断摘要与已执行步骤。">
      <template #actions>
        <a-button @click="load"><ReloadOutlined /> 刷新</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="filter-bar">
        <a-select v-model:value="filters.status" style="width: 160px" allow-clear placeholder="全部状态" @change="load">
          <a-select-option v-for="(label, value) in statusLabels" :key="value" :value="value">{{ label }}</a-select-option>
        </a-select>
        <a-input-search v-model:value="filters.q" placeholder="搜索标题、工单号或型号" style="width: 280px" @search="load" />
        <span class="muted">共 {{ tickets.length }} 张</span>
      </div>

      <a-spin :spinning="loading">
        <a-table :data-source="tickets" :columns="columns" :pagination="{ pageSize: 12 }" row-key="id" size="middle">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'ticket'">
              <div class="ticket-title">{{ record.title }}</div>
              <div class="tiny">{{ record.ticket_no }} · {{ record.model_id || '未关联型号' }}</div>
            </template>
            <template v-else-if="column.key === 'user'">{{ record.user?.username || '—' }}</template>
            <template v-else-if="column.key === 'status'">
              <StatusTag kind="ticket" :status="record.status" :label="record.status_label" />
            </template>
            <template v-else-if="column.key === 'priority'">
              <StatusTag kind="priority" :status="record.priority" />
            </template>
            <template v-else-if="column.key === 'assignee'">{{ record.assignee?.username || '待分配' }}</template>
            <template v-else-if="column.key === 'time'">{{ formatTime(record.created_at) }}</template>
            <template v-else-if="column.key === 'action'">
              <a @click="openDetail(record.id)">处理</a>
            </template>
          </template>
        </a-table>
      </a-spin>
    </div>

    <a-drawer v-model:open="drawerOpen" :width="700" title="工单处理" placement="right">
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <div class="detail-head">
            <div>
              <div class="detail-title">{{ detail.title }}</div>
              <div class="tiny">{{ detail.ticket_no }} · 用户 {{ detail.user?.username }}</div>
            </div>
            <StatusTag kind="ticket" :status="detail.status" :label="detail.status_label" />
          </div>

          <div class="meta-grid">
            <div><span class="muted">型号</span><div>{{ detail.model_id || '—' }}</div></div>
            <div><span class="muted">故障类别</span><div>{{ detail.fault_category || '—' }}</div></div>
            <div><span class="muted">错误码</span><div>{{ detail.brand_error_code || '—' }}</div></div>
            <div><span class="muted">联系方式（脱敏）</span><div>{{ detail.contact || '—' }}</div></div>
            <div><span class="muted">优先级</span><StatusTag kind="priority" :status="detail.priority" /></div>
            <div><span class="muted">创建时间</span><div>{{ formatTime(detail.created_at) }}</div></div>
          </div>

          <div class="detail-section">
            <h4>问题描述</h4>
            <p>{{ detail.summary || '—' }}</p>
          </div>

          <div v-if="detail.executed_steps?.length" class="detail-section">
            <h4>已执行步骤</h4>
            <div v-for="step in detail.executed_steps" :key="step.step_no" class="exec-step">
              <span>{{ step.step_no }}. {{ step.instruction }}</span>
              <a-tag>{{ step.status }}</a-tag>
            </div>
          </div>

          <div class="detail-section">
            <h4>处理记录</h4>
            <div class="events">
              <div v-for="event in detail.events" :key="event.id" class="event">
                <div class="event-head">
                  <span>{{ eventLabel(event.event_type) }}<a-tag v-if="event.internal" style="margin-left: 6px">内部</a-tag></span>
                  <span class="tiny">{{ formatTime(event.created_at) }}</span>
                </div>
                <div class="event-text">{{ event.content }}</div>
              </div>
            </div>
          </div>

          <div class="detail-section process">
            <h4>处理操作</h4>
            <a-form layout="vertical">
              <div class="form-grid">
                <a-form-item label="更新状态">
                  <a-select v-model:value="updateForm.status" allow-clear placeholder="不修改">
                    <a-select-option v-if="detail.status === 'pending'" value="assigned">已分配</a-select-option>
                    <a-select-option value="processing">处理中</a-select-option>
                    <a-select-option value="waiting_user">待用户确认</a-select-option>
                    <a-select-option value="resolved">已解决</a-select-option>
                    <a-select-option value="escalated">转专业维修</a-select-option>
                    <a-select-option value="closed">关闭</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="分配客服">
                  <a-select v-model:value="updateForm.assignee_id" allow-clear placeholder="不修改" show-search option-filter-prop="label">
                    <a-select-option v-for="user in assignees" :key="user.id" :value="user.id" :label="user.username">
                      {{ user.username }}（{{ user.role }}）
                    </a-select-option>
                  </a-select>
                </a-form-item>
              </div>
              <a-form-item label="处理结果">
                <a-textarea v-model:value="updateForm.resolution" :rows="2" />
              </a-form-item>
              <a-form-item label="处理备注 / 内部记录">
                <a-textarea v-model:value="updateForm.note" :rows="2" />
              </a-form-item>
              <a-checkbox v-model:checked="updateForm.internal">内部备注（用户不可见）</a-checkbox>
              <div style="margin-top: 12px">
                <a-button type="primary" :loading="saving" @click="saveUpdate">保存处理</a-button>
              </div>
            </a-form>
          </div>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import {
  adminGetTicket,
  adminListTickets,
  adminUpdateTicket,
  getAssignees,
} from '../../api/tickets'

const statusLabels = {
  pending: '待受理',
  assigned: '已分配',
  processing: '处理中',
  waiting_user: '待用户确认',
  resolved: '已解决',
  closed: '已关闭',
  escalated: '已转专业维修',
}
const columns = [
  { title: '工单', key: 'ticket', dataIndex: 'title' },
  { title: '用户', key: 'user', width: 100 },
  { title: '状态', key: 'status', width: 120 },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '客服', key: 'assignee', width: 100 },
  { title: '创建时间', key: 'time', width: 170 },
  { title: '操作', key: 'action', width: 70 },
]
const tickets = ref([])
const assignees = ref([])
const filters = ref({ status: undefined, q: '' })
const loading = ref(false)
const drawerOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const saving = ref(false)
const updateForm = ref({ status: undefined, assignee_id: undefined, note: '', resolution: '', internal: true })

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}
function eventLabel(type) {
  return {
    created: '创建',
    assigned: '分配',
    status_changed: '状态更新',
    comment: '备注',
    closed: '关闭',
  }[type] || type
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.q) params.q = filters.value.q
    const res = await adminListTickets(params)
    tickets.value = res.data
  } finally {
    loading.value = false
  }
}

async function openDetail(id) {
  drawerOpen.value = true
  detailLoading.value = true
  updateForm.value = { status: undefined, assignee_id: undefined, note: '', resolution: '', internal: true }
  try {
    const res = await adminGetTicket(id)
    detail.value = res.data
  } finally {
    detailLoading.value = false
  }
}

async function saveUpdate() {
  const payload = {}
  if (updateForm.value.status) payload.status = updateForm.value.status
  if (updateForm.value.assignee_id) payload.assignee_id = updateForm.value.assignee_id
  if (updateForm.value.note) payload.note = updateForm.value.note
  if (updateForm.value.resolution) payload.resolution = updateForm.value.resolution
  payload.internal = updateForm.value.internal
  if (!Object.keys(payload).length) {
    message.warning('没有需要保存的修改')
    return
  }
  saving.value = true
  try {
    const res = await adminUpdateTicket(detail.value.id, payload)
    detail.value = res.data
    message.success('已更新')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const res = await getAssignees()
  assignees.value = res.data
  await load()
})
</script>

<style scoped>
.ticket-title {
  font-weight: 600;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.detail-title {
  font-size: 17px;
  font-weight: 650;
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
  font-size: 13px;
}
.detail-section {
  margin-top: 18px;
}
.detail-section h4 {
  font-size: 13.5px;
  margin: 0 0 6px;
}
.detail-section p {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}
.exec-step {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12.5px;
  padding: 6px 0;
  color: var(--color-text-secondary);
}
.events {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
}
.event {
  border-left: 2px solid var(--color-border);
  padding-left: 10px;
}
.event-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.event-text {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
</style>