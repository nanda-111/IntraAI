<template>
  <div v-if="sources?.length" class="source-list">
    <div v-for="(source, index) in sources" :key="source.doc_id || index" class="source-card">
      <div class="source-head">
        <span class="source-index">E{{ index + 1 }}</span>
        <span class="source-title">{{ source.title }}</span>
        <a-tag v-if="source.authority_level" class="level">来源 {{ source.authority_level }}</a-tag>
        <a-tag v-if="source.risk_level" :color="riskColor(source.risk_level)">
          {{ source.risk_level }}
        </a-tag>
      </div>
      <div class="source-meta">
        <span v-if="source.model_scope">适用：{{ source.model_scope }}</span>
        <span v-if="source.version">版本：{{ source.version }}</span>
        <span v-if="source.fault_category">类别：{{ source.fault_category }}</span>
      </div>
      <div v-if="source.safety_warnings?.length" class="source-warn">
        <SafetyCertificateOutlined />
        {{ source.safety_warnings.join('；') }}
      </div>
      <a
        v-if="source.url"
        :href="source.url"
        target="_blank"
        rel="noopener noreferrer"
        class="source-link"
      >
        查看来源 <ExportOutlined />
      </a>
    </div>
  </div>
</template>

<script setup>
import { ExportOutlined, SafetyCertificateOutlined } from '@ant-design/icons-vue'

defineProps({
  sources: { type: Array, default: () => [] },
})

function riskColor(level) {
  return { L1: 'green', L2: 'orange', L3: 'red' }[level] || 'default'
}
</script>

<style scoped>
.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.source-card {
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--color-bg-elevated);
}
.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.source-index {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-primary);
  background: var(--color-primary-light);
  padding: 1px 6px;
  border-radius: 4px;
}
.source-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.level {
  font-size: 11px;
}
.source-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 5px;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.source-warn {
  margin-top: 6px;
  font-size: 12px;
  color: #b45309;
  background: #fffbeb;
  border-radius: 6px;
  padding: 5px 8px;
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.source-link {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-primary);
  text-decoration: none;
}
</style>