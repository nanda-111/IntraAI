<template>
  <div class="page">
    <PageHeader title="我的服务记录" subtitle="诊断、咨询和工单都按账号隔离；可继续未完成的诊断或重新咨询。" />

    <div class="page-body">
      <a-tabs v-model:activeKey="tab" class="history-tabs">
        <a-tab-pane key="diagnosis" tab="诊断历史">
          <a-spin :spinning="loading">
            <a-empty v-if="!diagnoses.length" description="暂无诊断记录" />
            <a-table
              v-else
              :data-source="diagnoses"
              :columns="diagnosisColumns"
              :pagination="{ pageSize: 10 }"
              row-key="id"
              size="middle"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'model'">
                  <div>{{ record.model_name || '未确认型号' }}</div>
                  <div class="tiny">{{ record.fault_category_label }}</div>
                </template>
                <template v-else-if="column.key === 'status'">
                  <StatusTag kind="diagnosis" :status="record.status" />
                </template>
                <template v-else-if="column.key === 'time'">
                  {{ formatTime(record.updated_at) }}
                </template>
                <template v-else-if="column.key === 'action'">
                  <router-link :to="`/diagnosis/${record.id}`">查看详情</router-link>
                </template>
              </template>
            </a-table>
          </a-spin>
        </a-tab-pane>

        <a-tab-pane key="assistant" tab="咨询历史">
          <a-spin :spinning="loading">
            <a-empty v-if="!sessions.length" description="暂无咨询记录" />
            <div v-else class="session-records">
              <router-link
                v-for="item in sessions"
                :key="item.id"
                :to="{ path: '/assistant', query: { session: item.id } }"
                class="session-record"
              >
                <div>
                  <div class="record-title">{{ item.title }}</div>
                  <div class="tiny">{{ item.last_message || '暂无消息' }}</div>
                </div>
                <div class="record-meta">
                  <span class="tiny">{{ item.message_count }} 条消息</span>
                  <span class="tiny">{{ formatTime(item.updated_at) }}</span>
                </div>
              </router-link>
            </div>
          </a-spin>
        </a-tab-pane>

        <a-tab-pane key="tickets" tab="售后工单">
          <a-spin :spinning="loading">
            <a-empty v-if="!tickets.length" description="暂无工单" />
            <a-table
              v-else
              :data-source="tickets"
              :columns="ticketColumns"
              :pagination="{ pageSize: 10 }"
              row-key="id"
              size="middle"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <StatusTag kind="ticket" :status="record.status" :label="record.status_label" />
                </template>
                <template v-else-if="column.key === 'time'">
                  {{ formatTime(record.created_at) }}
                </template>
                <template v-else-if="column.key === 'action'">
                  <router-link :to="`/tickets/${record.id}`">查看</router-link>
                </template>
              </template>
            </a-table>
          </a-spin>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { listDiagnoses } from '../../api/diagnosis'
import { listSessions } from '../../api/assistant'
import { listTickets } from '../../api/tickets'

const tab = ref('diagnosis')
const loading = ref(false)
const diagnoses = ref([])
const sessions = ref([])
const tickets = ref([])

const diagnosisColumns = [
  { title: '型号 / 故障', key: 'model', dataIndex: 'model_name' },
  { title: '现象', dataIndex: 'symptom', ellipsis: true },
  { title: '状态', key: 'status' },
  { title: '更新时间', key: 'time' },
  { title: '操作', key: 'action', width: 100 },
]
const ticketColumns = [
  { title: '工单号', dataIndex: 'ticket_no', width: 170 },
  { title: '标题', dataIndex: 'title', ellipsis: true },
  { title: '状态', key: 'status', width: 120 },
  { title: '创建时间', key: 'time', width: 180 },
  { title: '操作', key: 'action', width: 80 },
]

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

onMounted(async () => {
  loading.value = true
  try {
    const [d, s, t] = await Promise.allSettled([listDiagnoses(), listSessions(), listTickets()])
    if (d.status === 'fulfilled') diagnoses.value = d.value.data
    if (s.status === 'fulfilled') sessions.value = s.value.data
    if (t.status === 'fulfilled') tickets.value = t.value.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.history-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}
.session-records {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.session-record {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 12px 14px;
  text-decoration: none;
  color: inherit;
}
.session-record:hover {
  border-color: var(--color-primary);
}
.record-title {
  font-size: 13.5px;
  font-weight: 600;
  margin-bottom: 2px;
}
.record-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
</style>