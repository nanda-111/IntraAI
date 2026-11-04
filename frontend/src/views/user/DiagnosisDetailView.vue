<template>
  <div class="page">
    <PageHeader :title="`诊断详情 ${session?.session_id || ''}`" :subtitle="session?.summary || '查看诊断时间线、步骤与证据来源'" back>
      <template #actions>
        <a-button v-if="canContinue" type="primary" @click="$router.push({ path: '/diagnosis', query: { id: session.id } })">
          继续诊断
        </a-button>
        <a-button v-if="session?.escalation_required" @click="ticketModal = true">创建工单</a-button>
        <a-button v-if="canClose" @click="close(true)">标记已解决</a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <div v-if="session" class="page-body">
        <div class="panel summary">
          <div>
            <div class="model-name">{{ session.product.model_name || '未确认型号' }}</div>
            <div class="tiny">
              {{ session.product.brand || '—' }} · {{ session.product.region }} · {{ session.fault.category_label }}
              <span v-if="session.fault.brand_error_code"> · 代码 {{ session.fault.brand_error_code }}</span>
            </div>
          </div>
          <StatusTag kind="diagnosis" :status="session.diagnosis_state" />
        </div>

        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>诊断时间线</span></div>
            <div class="timeline">
              <div v-for="turn in session.turns" :key="turn.id" class="turn" :class="turn.role">
                <div class="turn-head">
                  <span>{{ turn.role === 'user' ? '用户' : '诊断助手' }}</span>
                  <span class="tiny">{{ formatTime(turn.created_at) }}</span>
                </div>
                <div class="turn-content">{{ turn.content }}</div>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title"><span>执行步骤</span></div>
            <a-empty v-if="!session.steps.length" description="暂无步骤" :image="simpleImage" />
            <div v-else class="step-list">
              <div v-for="step in session.steps" :key="step.step_id" class="step">
                <div class="step-head">
                  <span class="step-no">{{ step.step_no }}</span>
                  <span class="step-text">{{ step.instruction }}</span>
                  <a-tag>{{ statusLabel(step.status) }}</a-tag>
                </div>
                <div class="step-meta">
                  <StatusTag kind="risk" :status="step.risk_level" />
                  <span v-if="step.expected_result" class="tiny">预期：{{ step.expected_result }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title"><span>证据来源</span></div>
          <SourceList :sources="session.sources" />
          <a-empty v-if="!session.sources?.length" description="没有通过校验的证据" :image="simpleImage" />
        </div>
      </div>
    </a-spin>

    <a-modal v-model:open="ticketModal" title="创建售后工单" ok-text="确认提交" @ok="createTicket">
      <a-form layout="vertical">
        <a-form-item label="联系方式（可选）">
          <a-input v-model:value="contact" placeholder="手机号或邮箱" />
        </a-form-item>
        <a-form-item label="问题摘要">
          <a-textarea v-model:value="summary" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import SourceList from '../../components/SourceList.vue'
import { closeDiagnosis, getDiagnosis } from '../../api/diagnosis'
import { createTicket as createTicketApi } from '../../api/tickets'

const route = useRoute()
const router = useRouter()
const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const session = ref(null)
const loading = ref(false)
const ticketModal = ref(false)
const contact = ref('')
const summary = ref('')

const canContinue = computed(
  () =>
    session.value &&
    ['MODEL_PENDING', 'COLLECTING', 'RETRIEVING', 'STEP_READY', 'WAIT_USER_ACTION'].includes(
      session.value.diagnosis_state,
    ),
)
const canClose = computed(
  () => session.value && !['RESOLVED', 'CLOSED', 'CANCELLED', 'TICKET_OPEN'].includes(session.value.diagnosis_state),
)

function statusLabel(status) {
  return { done: '已完成', failed: '未解决', skipped: '无法执行', ready: '待执行', pending: '未开始' }[status] || status
}
function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

async function load() {
  loading.value = true
  try {
    const res = await getDiagnosis(route.params.id)
    session.value = res.data
    summary.value = res.data.summary || res.data.symptoms || ''
  } catch (err) {
    message.error(err.response?.data?.detail || '诊断加载失败')
  } finally {
    loading.value = false
  }
}

async function close(resolved) {
  try {
    const res = await closeDiagnosis(route.params.id, { resolved, note: resolved ? '用户确认已解决' : '结束诊断' })
    session.value = res.data
    message.success('已更新诊断状态')
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

async function createTicket() {
  try {
    const res = await createTicketApi({
      diagnosis_id: Number(route.params.id),
      contact: contact.value || undefined,
      summary: summary.value || undefined,
    })
    ticketModal.value = false
    message.success('工单已创建')
    router.push(`/tickets/${res.data.id}`)
  } catch (err) {
    message.error(err.response?.data?.detail || '创建工单失败')
  }
}

onMounted(load)
</script>

<style scoped>
.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.model-name {
  font-size: 17px;
  font-weight: 650;
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
}
.turn {
  border-left: 2px solid var(--color-border);
  padding: 2px 0 2px 12px;
}
.turn.user {
  border-color: var(--color-primary);
}
.turn-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}
.turn-content {
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.step-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.step {
  border: 1px solid var(--color-border-light);
  border-radius: 9px;
  padding: 10px 12px;
}
.step-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}
.step-no {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-text {
  flex: 1;
  line-height: 1.55;
}
.step-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  padding-left: 28px;
}
</style>