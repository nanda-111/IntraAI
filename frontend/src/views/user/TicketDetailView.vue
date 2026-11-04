<template>
  <div class="page">
    <PageHeader :title="ticket ? `工单 ${ticket.ticket_no}` : '工单详情'" :subtitle="ticket?.title" back>
      <template #actions>
        <a-button v-if="ticket && ticket.status !== 'closed'" @click="closeTicket">关闭工单</a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <div v-if="ticket" class="page-body">
        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>工单信息</span></div>
            <div class="info-row"><span>状态</span><StatusTag kind="ticket" :status="ticket.status" :label="ticket.status_label" /></div>
            <div class="info-row"><span>优先级</span><StatusTag kind="priority" :status="ticket.priority" /></div>
            <div class="info-row"><span>型号</span><span>{{ ticket.model_id || '—' }}</span></div>
            <div class="info-row"><span>故障类别</span><span>{{ ticket.fault_category || '—' }}</span></div>
            <div class="info-row"><span>错误码</span><span>{{ ticket.brand_error_code || '—' }}</span></div>
            <div class="info-row"><span>创建时间</span><span>{{ formatTime(ticket.created_at) }}</span></div>
            <div class="info-row"><span>处理客服</span><span>{{ ticket.assignee?.username || '待分配' }}</span></div>
            <div v-if="ticket.resolution" class="info-row"><span>处理结果</span><span>{{ ticket.resolution }}</span></div>
          </div>
          <div class="panel">
            <div class="panel-title"><span>问题描述</span></div>
            <p class="summary">{{ ticket.summary || '—' }}</p>
            <div v-if="ticket.executed_steps?.length" class="subsection">
              <div class="section-title">已执行步骤</div>
              <div v-for="step in ticket.executed_steps" :key="step.step_no" class="exec-step">
                <span>{{ step.step_no }}. {{ step.instruction }}</span>
                <a-tag>{{ step.status }}</a-tag>
              </div>
            </div>
          </div>
        </div>

        <div v-if="ticket.evidence?.length" class="panel">
          <div class="panel-title"><span>诊断证据</span></div>
          <SourceList :sources="ticket.evidence" />
        </div>

        <div class="panel">
          <div class="panel-title"><span>处理记录</span></div>
          <div class="events">
            <div v-for="event in ticket.events" :key="event.id" class="event">
              <div class="event-head">
                <span class="event-type">{{ eventLabel(event.event_type) }}</span>
                <span class="tiny">{{ formatTime(event.created_at) }}</span>
              </div>
              <div class="event-text">{{ event.content || '—' }}</div>
              <div v-if="event.before_status && event.before_status !== event.after_status" class="tiny">
                {{ event.before_status }} → {{ event.after_status }}
              </div>
            </div>
          </div>
          <div v-if="ticket.status !== 'closed'" class="comment-box">
            <a-textarea v-model:value="comment" :rows="2" placeholder="补充说明或回复客服" />
            <a-button type="primary" :disabled="!comment.trim()" @click="sendComment">发送</a-button>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute } from 'vue-router'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import SourceList from '../../components/SourceList.vue'
import { closeTicket as closeTicketApi, commentTicket, getTicket } from '../../api/tickets'

const route = useRoute()
const ticket = ref(null)
const loading = ref(false)
const comment = ref('')

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}
function eventLabel(type) {
  return {
    created: '创建工单',
    assigned: '分配',
    status_changed: '状态更新',
    comment: '沟通记录',
    closed: '关闭',
  }[type] || type
}

async function load() {
  loading.value = true
  try {
    const res = await getTicket(route.params.id)
    ticket.value = res.data
  } catch (err) {
    message.error(err.response?.data?.detail || '工单加载失败')
  } finally {
    loading.value = false
  }
}

async function sendComment() {
  if (!comment.value.trim()) return
  try {
    const res = await commentTicket(route.params.id, comment.value.trim())
    ticket.value = res.data
    comment.value = ''
  } catch (err) {
    message.error(err.response?.data?.detail || '发送失败')
  }
}

async function closeTicket() {
  try {
    const res = await closeTicketApi(route.params.id, '用户确认问题已解决')
    ticket.value = res.data
    message.success('工单已关闭')
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(load)
</script>

<style scoped>
.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 13px;
}
.info-row:last-child {
  border-bottom: none;
}
.info-row > span:first-child {
  color: var(--color-text-tertiary);
}
.summary {
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
}
.subsection {
  margin-top: 16px;
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
  gap: 10px;
}
.event {
  border-left: 2px solid var(--color-border);
  padding-left: 12px;
}
.event-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.event-type {
  font-weight: 600;
}
.event-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 2px;
  white-space: pre-wrap;
}
.comment-box {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  align-items: flex-end;
}
</style>