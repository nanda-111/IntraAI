<template>
  <div class="page">
    <PageHeader title="运营概览" subtitle="型号覆盖、知识审核、诊断解决率、工单积压与检索质量。">
      <template #actions>
        <a-select v-model:value="brand" style="width: 160px" allow-clear placeholder="全部品牌" @change="load">
          <a-select-option v-for="item in brands" :key="item.brand_code" :value="item.brand_code">
            {{ item.name }}
          </a-select-option>
        </a-select>
        <a-button @click="load"><ReloadOutlined /> 刷新</a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <div v-if="data" class="page-body">
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-label">支持型号</div>
            <div class="stat-value">{{ data.models.active }}</div>
            <div class="stat-hint">共 {{ data.models.total }} 个型号登记</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">已发布知识</div>
            <div class="stat-value">{{ data.knowledge.published }}</div>
            <div class="stat-hint">待审核 {{ data.knowledge.pending_review }} 条</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">诊断解决率</div>
            <div class="stat-value">{{ percent(data.diagnosis.resolution_rate) }}</div>
            <div class="stat-hint">{{ data.diagnosis.resolved }} / {{ data.diagnosis.total }} 已解决</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">待处理工单</div>
            <div class="stat-value">{{ data.tickets.open }}</div>
            <div class="stat-hint">累计 {{ data.tickets.total }} 张工单</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">咨询会话</div>
            <div class="stat-value">{{ data.chat.sessions }}</div>
            <div class="stat-hint">智能客服累计会话</div>
          </div>
        </div>

        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>故障类型分布</span></div>
            <a-empty v-if="!data.fault_distribution.length" description="暂无诊断数据" :image="simpleImage" />
            <div v-else class="bars">
              <div v-for="item in data.fault_distribution" :key="item.category" class="bar-row">
                <span class="bar-label">{{ item.label }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: barWidth(item.count) }" />
                </div>
                <span class="bar-value">{{ item.count }}</span>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title"><span>工单状态</span></div>
            <a-empty v-if="!Object.keys(data.tickets.by_status).length" description="暂无工单" :image="simpleImage" />
            <div v-else class="status-grid">
              <div v-for="(count, status) in data.tickets.by_status" :key="status" class="status-card">
                <div class="status-label">{{ data.tickets.labels[status] || status }}</div>
                <div class="status-count">{{ count }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>品牌知识覆盖</span></div>
            <a-table
              :data-source="data.brand_coverage"
              :columns="coverageColumns"
              :pagination="false"
              size="small"
              row-key="brand_code"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'models'">{{ record.active_model_count }} / {{ record.model_count }}</template>
                <template v-else-if="column.key === 'knowledge'">
                  {{ record.published_count }} / {{ record.knowledge_count }}
                </template>
              </template>
            </a-table>
          </div>

          <div class="panel">
            <div class="panel-title">
              <span>最近评测</span>
              <router-link to="/admin/evaluation" class="link">评测中心</router-link>
            </div>
            <template v-if="data.evaluation.latest_run">
              <div class="metric-grid">
                <template v-for="(value, key) in data.evaluation.latest_run.metrics" :key="key">
                  <div v-if="!['note', 'items_with_expected_docs'].includes(key)" class="metric">
                    <div class="metric-label">{{ metricLabel(key) }}</div>
                    <div class="metric-value">{{ formatMetric(value) }}</div>
                  </div>
                </template>
              </div>
              <p class="tiny" style="margin-top: 10px">指标基于当前测试集真实计算结果，不代表全量线上效果。</p>
            </template>
            <a-empty v-else description="尚未运行评测" :image="simpleImage" />
          </div>
        </div>

        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>最近诊断</span></div>
            <a-empty v-if="!data.recent_diagnoses.length" description="暂无" :image="simpleImage" />
            <div v-else class="recent-list">
              <div v-for="item in data.recent_diagnoses" :key="item.id" class="recent">
                <div>{{ item.model_id || '未确认型号' }}</div>
                <div class="tiny">{{ item.fault_category_label || '未分类' }}</div>
                <StatusTag kind="diagnosis" :status="item.status" />
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-title"><span>最近工单</span></div>
            <a-empty v-if="!data.recent_tickets.length" description="暂无" :image="simpleImage" />
            <div v-else class="recent-list">
              <div v-for="item in data.recent_tickets" :key="item.id" class="recent">
                <div>{{ item.title }}</div>
                <div class="tiny">{{ item.ticket_no }}</div>
                <StatusTag kind="ticket" :status="item.status" :label="item.status_label" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Empty } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { getDashboard } from '../../api/overview'
import { getBrands } from '../../api/products'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const data = ref(null)
const brands = ref([])
const brand = ref(undefined)
const loading = ref(false)

const coverageColumns = [
  { title: '品牌', dataIndex: 'brand_name' },
  { title: '支持型号', key: 'models' },
  { title: '已发布知识', key: 'knowledge' },
]
const maxFault = computed(() =>
  Math.max(1, ...(data.value?.fault_distribution || []).map((item) => item.count)),
)

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`
}
function barWidth(count) {
  return `${Math.round((count / maxFault.value) * 100)}%`
}
function metricLabel(key) {
  return (
    {
      recall_at_5: 'Recall@5',
      mrr_at_5: 'MRR@5',
      fault_accuracy: '故障分类准确率',
      escalation_recall: '转人工召回率',
      avg_latency_ms: '平均耗时(ms)',
      items_with_expected_docs: '含标准证据题数',
    }[key] || key
  )
}
function formatMetric(value) {
  return typeof value === 'number' ? value.toFixed(2) : value
}

async function load() {
  loading.value = true
  try {
    const params = brand.value ? { brand: brand.value } : {}
    const res = await getDashboard(params)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const res = await getBrands()
  brands.value = res.data
  await load()
})
</script>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bar-row {
  display: grid;
  grid-template-columns: 110px 1fr 36px;
  gap: 10px;
  align-items: center;
  font-size: 12.5px;
}
.bar-label {
  color: var(--color-text-secondary);
}
.bar-track {
  height: 8px;
  border-radius: 999px;
  background: var(--color-bg-sunken);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--color-primary), #7c5cfc);
}
.bar-value {
  text-align: right;
  color: var(--color-text-tertiary);
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.status-card {
  border: 1px solid var(--color-border-light);
  border-radius: 9px;
  padding: 12px;
}
.status-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.status-count {
  font-size: 22px;
  font-weight: 700;
  margin-top: 2px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.metric {
  border: 1px solid var(--color-border-light);
  border-radius: 9px;
  padding: 10px;
}
.metric-label {
  font-size: 11.5px;
  color: var(--color-text-tertiary);
}
.metric-value {
  font-size: 18px;
  font-weight: 650;
}
.recent-list {
  display: flex;
  flex-direction: column;
}
.recent {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 10px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 13px;
}
.recent:last-child {
  border-bottom: none;
}
.recent .tiny {
  grid-column: 1;
}
.recent :deep(.status-tag) {
  grid-row: 1 / span 2;
  grid-column: 2;
}
.link {
  font-size: 12.5px;
  color: var(--color-primary);
  text-decoration: none;
}
</style>