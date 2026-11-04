<template>
  <div class="page">
    <PageHeader
      title="故障诊断工作台"
      subtitle="按型号确认、证据检索、单步执行的流程排查故障；高风险操作会被拦截。"
      back
    />

    <div v-if="!session" class="page-body">
      <div class="panel setup">
        <div class="setup-title">创建诊断</div>
        <p class="muted">
          平台只对“已支持”型号开放型号专属诊断。一次只推送一条步骤，执行后请反馈结果。
        </p>
        <a-form layout="vertical">
          <a-form-item label="打印机型号" required>
            <ModelSelect v-model="form.model_id" />
          </a-form-item>
          <a-form-item label="故障类别">
            <a-select v-model:value="form.fault_category" allow-clear placeholder="可选，不确定可留空">
              <a-select-option v-for="item in categories" :key="item.code" :value="item.code">
                {{ item.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="故障现象">
            <a-textarea
              v-model:value="form.symptom"
              :rows="3"
              placeholder="例如：HP DeskJet 2720 显示 E4，纸张进不去，已经重新装纸"
            />
          </a-form-item>
          <a-button type="primary" :loading="creating" @click="startDiagnosis">
            开始诊断
          </a-button>
        </a-form>
      </div>
      <div class="panel">
        <div class="panel-title"><span>诊断流程</span></div>
        <div class="flow">
          <div v-for="(step, index) in flow" :key="step" class="flow-step">
            <span class="flow-no">{{ index + 1 }}</span>
            <span>{{ step }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="page-body">
      <div class="product-bar panel">
        <div class="product-main">
          <div class="product-name">
            {{ session.product.model_name || '未确认型号' }}
            <StatusTag kind="diagnosis" :status="session.diagnosis_state" />
          </div>
          <div class="tiny">
            {{ session.product.brand || '—' }} · {{ session.product.region }} ·
            {{ session.fault.category_label }}
            <span v-if="session.fault.brand_error_code"> · 代码 {{ session.fault.brand_error_code }}</span>
          </div>
        </div>
        <div class="progress">
          <a-progress
            :percent="progressPercent"
            :format="() => `${doneCount}/${session.steps.length}`"
            size="small"
            style="width: 150px"
          />
        </div>
        <a-button size="small" @click="reset">新建诊断</a-button>
      </div>

      <div class="workspace">
        <div class="main-col">
          <div v-if="session.current_step" class="step-card">
            <div class="step-head">
              <div class="step-badge">第 {{ session.current_step.step_no }} 步 / 共 {{ session.steps.length }} 步</div>
              <StatusTag kind="risk" :status="session.current_step.risk_level" />
            </div>
            <div class="step-instruction">{{ session.current_step.instruction }}</div>
            <div v-if="session.current_step.expected_result" class="step-expected">
              预期结果：{{ session.current_step.expected_result }}
            </div>
            <div :class="['risk-banner', `risk-${session.current_step.risk_level}`]">
              <SafetyCertificateOutlined />
              <span v-if="session.current_step.risk_level === 'L2'">
                该步骤需要谨慎操作。请先阅读官方安全要求，若不确定请停止并转人工。
              </span>
              <span v-else>低风险步骤。执行后请如实反馈结果，平台不会重复已完成的步骤。</span>
            </div>
            <div class="step-actions">
              <a-button type="primary" @click="submitResult('done')">
                <CheckOutlined /> 已完成
              </a-button>
              <a-button @click="submitResult('failed')">还是不行</a-button>
              <a-button @click="submitResult('skipped')">无法执行</a-button>
            </div>
            <div v-if="session.current_step.source_title" class="step-source">
              来源：{{ session.current_step.source_title }}
              <a v-if="session.current_step.source_url" :href="session.current_step.source_url" target="_blank" rel="noopener noreferrer">查看原文</a>
            </div>
          </div>

          <div v-else-if="session.diagnosis_state === 'MODEL_PENDING'" class="step-card">
            <div class="step-title">请先确认打印机型号</div>
            <ModelSelect v-model="confirmModelId" />
            <a-button type="primary" style="margin-top: 12px" @click="confirmModel">确认型号</a-button>
            <p class="muted" style="margin-top: 10px">
              也可以直接在下方输入完整型号，例如 “HP DeskJet 2720”。
            </p>
          </div>

          <div v-else-if="session.diagnosis_state === 'WAIT_USER_ACTION'" class="step-card">
            <div class="step-title">所有已审核步骤已执行</div>
            <p class="muted">问题是否已经解决？</p>
            <div class="step-actions">
              <a-button type="primary" @click="resolve(true)">已解决</a-button>
              <a-button @click="escalate">仍未解决，转人工</a-button>
            </div>
          </div>

          <div v-else-if="session.diagnosis_state === 'ESCALATED'" class="step-card escalation-card">
            <div class="step-title">建议转人工处理</div>
            <p class="muted">{{ lastAssistantText }}</p>
            <a-button type="primary" @click="ticketModal = true">提交售后工单</a-button>
          </div>

          <div v-else-if="session.diagnosis_state === 'RESOLVED'" class="step-card success-card">
            <div class="step-title">本次诊断已解决</div>
            <p class="muted">{{ session.summary }}</p>
            <a-button @click="reset">开始新的诊断</a-button>
          </div>

          <div class="panel timeline-panel">
            <div class="panel-title"><span>诊断记录</span></div>
            <div class="timeline">
              <div v-for="turn in session.turns" :key="turn.id" class="turn" :class="turn.role">
                <span class="turn-role">{{ turn.role === 'user' ? '你' : '助手' }}</span>
                <span class="turn-content">{{ turn.content }}</span>
              </div>
            </div>
          </div>

          <div class="composer panel">
            <a-textarea
              v-model:value="messageText"
              :auto-size="{ minRows: 1, maxRows: 3 }"
              placeholder="补充现象、错误码或灯态，例如：还是不行，纸卡在后部"
              :disabled="busy"
              @press-enter.prevent="sendMessage"
            />
            <a-button type="primary" :disabled="!messageText.trim()" :loading="busy" @click="sendMessage">
              发送
            </a-button>
          </div>
        </div>

        <aside class="side-col">
          <div class="panel">
            <div class="panel-title"><span>风险等级</span></div>
            <div class="risk-legend">
              <div><StatusTag kind="risk" status="L1" /> 可观察、可自行确认</div>
              <div><StatusTag kind="risk" status="L2" /> 按官方要求谨慎操作</div>
              <div><StatusTag kind="risk" status="L3" /> 禁止自助拆修</div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-title"><span>证据来源</span></div>
            <SourceList :sources="session.sources" />
            <a-empty v-if="!session.sources?.length" description="暂无适用证据" :image="simpleImage" />
          </div>
          <div class="panel">
            <div class="panel-title"><span>已执行步骤</span></div>
            <div class="step-list">
              <div v-for="step in session.steps" :key="step.step_id" class="step-row">
                <span class="step-num">{{ step.step_no }}</span>
                <span class="step-text">{{ step.instruction }}</span>
                <a-tag>{{ step.status }}</a-tag>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>

    <a-modal v-model:open="ticketModal" title="提交售后工单" ok-text="确认提交" cancel-text="取消" @ok="createTicket">
      <p class="muted">工单会自动携带型号、故障现象、已执行步骤和来源证据。</p>
      <a-form layout="vertical">
        <a-form-item label="联系方式（可选，用于客服联系）">
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
import { CheckOutlined, SafetyCertificateOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import ModelSelect from '../../components/ModelSelect.vue'
import SourceList from '../../components/SourceList.vue'
import { getDevices, getFaultCategories } from '../../api/products'
import {
  closeDiagnosis,
  confirmDiagnosisModel,
  createDiagnosis,
  getDiagnosis,
  sendDiagnosisMessage,
  submitStepResult,
} from '../../api/diagnosis'
import { createTicket as createTicketApi } from '../../api/tickets'

const route = useRoute()
const router = useRouter()
const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const categories = ref([])
const session = ref(null)
const creating = ref(false)
const busy = ref(false)
const messageText = ref('')
const confirmModelId = ref('')
const form = ref({ model_id: route.query.model_id || '', fault_category: undefined, symptom: '' })

const ticketModal = ref(false)
const contact = ref('')
const summary = ref('')

const flow = [
  '确认品牌与具体型号，校验型号支持状态',
  '收集现象、错误码/灯态和已尝试操作',
  '按型号硬过滤并检索已审核证据',
  '一次推送一条低风险步骤，等待反馈',
  '解决后归档，未解决转售后工单',
]

const doneCount = computed(
  () => session.value?.steps.filter((item) => ['done', 'failed', 'skipped'].includes(item.status)).length || 0,
)
const progressPercent = computed(() => {
  const total = session.value?.steps.length || 0
  return total ? Math.round((doneCount.value / total) * 100) : 0
})
const lastAssistantText = computed(() => {
  const turns = session.value?.turns || []
  const last = [...turns].reverse().find((item) => item.role === 'assistant')
  return last?.content || '当前资料不足或请求涉及高风险操作，建议提交工单转人工处理。'
})

function update(data) {
  session.value = data
}

async function startDiagnosis() {
  if (!form.value.model_id) {
    message.warning('请先选择打印机型号')
    return
  }
  creating.value = true
  try {
    const res = await createDiagnosis({
      model_id: form.value.model_id,
      symptom: form.value.symptom || undefined,
      fault_category: form.value.fault_category || undefined,
      region: 'CN',
    })
    update(res.data)
  } catch (err) {
    message.error(err.response?.data?.detail || '创建诊断失败')
  } finally {
    creating.value = false
  }
}

async function loadSession(id) {
  const res = await getDiagnosis(id)
  update(res.data)
}

async function submitResult(result) {
  if (!session.value.current_step) return
  busy.value = true
  try {
    const res = await submitStepResult(session.value.id, session.value.current_step.step_id, {
      result,
      note: `用户反馈：${result}`,
    })
    update(res.data)
    if (res.data.diagnosis_state === 'RESOLVED') message.success('已记录解决结果')
  } catch (err) {
    message.error(err.response?.data?.detail || '提交失败')
  } finally {
    busy.value = false
  }
}

async function sendMessage() {
  const content = messageText.value.trim()
  if (!content) return
  busy.value = true
  try {
    const res = await sendDiagnosisMessage(session.value.id, content)
    update(res.data)
    messageText.value = ''
  } catch (err) {
    message.error(err.response?.data?.detail || '发送失败')
  } finally {
    busy.value = false
  }
}

async function confirmModel() {
  if (!confirmModelId.value) return
  try {
    const res = await confirmDiagnosisModel(session.value.id, confirmModelId.value)
    update(res.data)
  } catch (err) {
    message.error(err.response?.data?.detail || '确认失败')
  }
}

async function resolve(resolved) {
  try {
    const res = await closeDiagnosis(session.value.id, { resolved, note: resolved ? '用户确认已解决' : '用户结束诊断' })
    update(res.data)
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

async function escalate() {
  try {
    const res = await sendDiagnosisMessage(session.value.id, '转人工处理')
    update(res.data)
    ticketModal.value = true
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

async function createTicket() {
  try {
    const res = await createTicketApi({
      diagnosis_id: session.value.id,
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

function reset() {
  session.value = null
  messageText.value = ''
  summary.value = ''
}

onMounted(async () => {
  const [catRes, deviceRes] = await Promise.allSettled([getFaultCategories(), getDevices()])
  if (catRes.status === 'fulfilled') categories.value = catRes.value.data
  if (deviceRes.status === 'fulfilled' && !form.value.model_id) {
    const current = deviceRes.value.data.find((item) => item.is_current)
    if (current) form.value.model_id = current.model_id
  }
  if (route.query.id) {
    await loadSession(route.query.id)
  }
})
</script>

<style scoped>
.setup {
  max-width: 680px;
}
.setup-title {
  font-size: 17px;
  font-weight: 650;
  margin-bottom: 4px;
}
.flow {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.flow-step {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.flow-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  font-weight: 600;
}
.product-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 20px;
}
.product-main {
  flex: 1;
}
.product-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 650;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280px, 1fr);
  gap: 16px;
  align-items: start;
}
.main-col,
.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.step-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-sm);
}
.step-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.step-badge {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.step-instruction {
  font-size: 18px;
  font-weight: 650;
  line-height: 1.6;
  margin: 12px 0;
}
.step-expected {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}
.step-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}
.step-source {
  margin-top: 14px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.step-source a {
  margin-left: 8px;
  color: var(--color-primary);
}
.step-title {
  font-size: 17px;
  font-weight: 650;
  margin-bottom: 10px;
}
.success-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.escalation-card {
  border-color: #fde68a;
  background: #fffbeb;
}
.timeline-panel {
  max-height: 360px;
  overflow-y: auto;
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.turn {
  display: flex;
  gap: 8px;
  font-size: 12.5px;
  line-height: 1.6;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--color-bg-sunken);
}
.turn.user {
  background: var(--color-primary-bg);
}
.turn-role {
  flex-shrink: 0;
  font-weight: 650;
  color: var(--color-text-secondary);
}
.turn-content {
  white-space: pre-wrap;
}
.composer {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 12px;
}
.risk-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
}
.step-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12px;
}
.step-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-bg-sunken);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  flex-shrink: 0;
}
.step-text {
  flex: 1;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>