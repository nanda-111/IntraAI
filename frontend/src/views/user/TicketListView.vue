<template>
  <div class="page">
    <PageHeader title="售后工单" subtitle="未解决的诊断或问题可提交售后工单，客服处理后在此跟踪状态。">
      <template #actions>
        <a-button type="primary" @click="createModal = true"><PlusOutlined /> 新建工单</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="filter-bar">
        <a-radio-group v-model:value="status" button-style="solid" @change="load">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="pending">待受理</a-radio-button>
          <a-radio-button value="processing">处理中</a-radio-button>
          <a-radio-button value="resolved">已解决</a-radio-button>
          <a-radio-button value="closed">已关闭</a-radio-button>
        </a-radio-group>
      </div>

      <a-spin :spinning="loading">
        <a-empty v-if="!tickets.length" description="暂无工单" />
        <div v-else class="ticket-list">
          <router-link v-for="ticket in tickets" :key="ticket.id" :to="`/tickets/${ticket.id}`" class="ticket-card">
            <div class="ticket-main">
              <div class="ticket-top">
                <span class="ticket-no">{{ ticket.ticket_no }}</span>
                <StatusTag kind="ticket" :status="ticket.status" :label="ticket.status_label" />
                <StatusTag kind="priority" :status="ticket.priority" />
              </div>
              <div class="ticket-title">{{ ticket.title }}</div>
              <div class="ticket-meta">
                <span v-if="ticket.model_id">{{ ticket.model_id }}</span>
                <span v-if="ticket.fault_category">{{ ticket.fault_category }}</span>
                <span>{{ formatTime(ticket.created_at) }}</span>
              </div>
            </div>
            <ArrowRightOutlined class="arrow" />
          </router-link>
        </div>
      </a-spin>
    </div>

    <a-modal v-model:open="createModal" title="新建售后工单" ok-text="提交" @ok="submitTicket">
      <a-form layout="vertical">
        <a-form-item label="标题" required>
          <a-input v-model:value="form.title" placeholder="例如：卡纸处理后仍无法打印" />
        </a-form-item>
        <a-form-item label="打印机型号">
          <ModelSelect v-model="form.model_id" />
        </a-form-item>
        <a-form-item label="问题描述">
          <a-textarea v-model:value="form.summary" :rows="3" placeholder="描述故障现象、错误码和已尝试的操作" />
        </a-form-item>
        <a-form-item label="联系方式">
          <a-input v-model:value="form.contact" placeholder="手机号或邮箱，仅用于客服联系" />
        </a-form-item>
        <a-form-item label="优先级">
          <a-select v-model:value="form.priority">
            <a-select-option value="low">低</a-select-option>
            <a-select-option value="normal">普通</a-select-option>
            <a-select-option value="high">高</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { ArrowRightOutlined, PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import ModelSelect from '../../components/ModelSelect.vue'
import { createTicket, listTickets } from '../../api/tickets'

const tickets = ref([])
const status = ref('')
const loading = ref(false)
const createModal = ref(false)
const form = ref({ title: '', model_id: '', summary: '', contact: '', priority: 'normal' })
const router = useRouter()

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

async function load() {
  loading.value = true
  try {
    const params = status.value ? { status: status.value } : {}
    const res = await listTickets(params)
    tickets.value = res.data
  } finally {
    loading.value = false
  }
}

async function submitTicket() {
  if (!form.value.title.trim()) {
    message.warning('请填写工单标题')
    return
  }
  try {
    const res = await createTicket({
      title: form.value.title,
      model_id: form.value.model_id || undefined,
      summary: form.value.summary || undefined,
      contact: form.value.contact || undefined,
      priority: form.value.priority,
    })
    createModal.value = false
    message.success('工单已创建')
    form.value = { title: '', model_id: '', summary: '', contact: '', priority: 'normal' }
    await load()
    router.push(`/tickets/${res.data.id}`)
  } catch (err) {
    message.error(err.response?.data?.detail || '创建失败')
  }
}

onMounted(load)
</script>

<style scoped>
.ticket-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ticket-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  text-decoration: none;
  color: inherit;
}
.ticket-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}
.ticket-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ticket-no {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--color-text-tertiary);
}
.ticket-title {
  font-size: 14.5px;
  font-weight: 600;
  margin: 6px 0 4px;
}
.ticket-meta {
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.arrow {
  color: var(--color-text-tertiary);
}
</style>