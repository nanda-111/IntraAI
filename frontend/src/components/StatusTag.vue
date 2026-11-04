<template>
  <a-tag :color="config.color" class="status-tag">{{ config.label }}</a-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: '' },
  label: { type: String, default: '' },
  kind: { type: String, default: 'generic' },
})

const maps = {
  generic: {},
  model: {
    planned: ['default', '规划中'],
    building: ['orange', '资料建设中'],
    pilot: ['blue', '试运行'],
    active: ['green', '已支持'],
    suspended: ['red', '暂停服务'],
  },
  review: {
    draft: ['default', '草稿'],
    pending: ['orange', '待审核'],
    approved: ['blue', '已通过'],
    published: ['green', '已发布'],
    rejected: ['red', '已退回'],
    archived: ['default', '已下架'],
  },
  ticket: {
    pending: ['orange', '待受理'],
    assigned: ['blue', '已分配'],
    processing: ['processing', '处理中'],
    waiting_user: ['gold', '待用户确认'],
    resolved: ['green', '已解决'],
    closed: ['default', '已关闭'],
    escalated: ['purple', '已转专业维修'],
  },
  diagnosis: {
    MODEL_PENDING: ['default', '待确认型号'],
    MODEL_CONFIRMED: ['blue', '型号已确认'],
    COLLECTING: ['blue', '收集信息'],
    RETRIEVING: ['processing', '检索中'],
    STEP_READY: ['cyan', '步骤就绪'],
    WAIT_USER_ACTION: ['gold', '等待反馈'],
    NEED_CLARIFICATION: ['orange', '需要澄清'],
    RESOLVED: ['green', '已解决'],
    ESCALATED: ['red', '建议转人工'],
    TICKET_OPEN: ['purple', '已建工单'],
    CLOSED: ['default', '已关闭'],
    CANCELLED: ['default', '已取消'],
  },
  priority: { low: ['default', '低'], normal: ['blue', '普通'], high: ['red', '高'] },
  risk: { L1: ['green', 'L1 低风险'], L2: ['orange', 'L2 谨慎操作'], L3: ['red', 'L3 高风险'] },
}

const config = computed(() => {
  const table = maps[props.kind] || {}
  const entry = table[props.status]
  if (entry) return { color: entry[0], label: props.label || entry[1] }
  const color =
    props.status === 'active' || props.status === 'published' || props.status === 'resolved'
      ? 'green'
      : 'default'
  return { color, label: props.label || props.status || '未知' }
})
</script>

<style scoped>
.status-tag {
  border-radius: 999px;
  margin-inline-end: 0;
}
</style>