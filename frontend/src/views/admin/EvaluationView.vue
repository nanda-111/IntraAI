<template>
  <div class="page">
    <PageHeader title="评测中心" subtitle="按品牌/型号维护测试集，运行检索、故障分类与转人工指标。所有指标均由真实检索结果计算。">
      <template #actions>
        <a-button type="primary" @click="datasetModal = true"><PlusOutlined /> 新建数据集</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="panel">
        <div class="panel-title"><span>测试集</span></div>
        <a-spin :spinning="loading">
          <a-table :data-source="datasets" :columns="datasetColumns" :pagination="false" row-key="id" size="middle">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <div class="name-cell">{{ record.name }}</div>
                <div class="tiny">{{ record.brand_code || '跨品牌' }} · {{ record.model_id || '不限型号' }}</div>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a @click="selectDataset(record)">查看题目</a>
                  <a @click="run(record)">运行评测</a>
                  <a class="danger-link" @click="removeDataset(record)">删除</a>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-spin>
      </div>

      <div v-if="selected" class="panel">
        <div class="panel-title">
          <span>{{ selected.name }} · 测试问题</span>
          <a-button size="small" @click="itemModal = true"><PlusOutlined /> 添加问题</a-button>
        </div>
        <a-table :data-source="items" :columns="itemColumns" :pagination="{ pageSize: 8 }" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'expected'">
              <span class="tiny">{{ (record.expected_doc_ids || []).join(', ') || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'escalation'">
              <a-tag :color="record.expected_escalation ? 'red' : 'default'">
                {{ record.expected_escalation ? '应转人工' : '正常回答' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a class="danger-link" @click="removeItem(record)">删除</a>
            </template>
          </template>
        </a-table>
      </div>

      <div class="panel">
        <div class="panel-title"><span>评测任务</span></div>
        <a-empty v-if="!runs.length" description="尚未运行评测" />
        <a-table v-else :data-source="runs" :columns="runColumns" :pagination="{ pageSize: 8 }" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'metrics'">
              <span class="tiny">
                Recall@5 {{ pct(record.metrics.recall_at_5) }} · MRR@5 {{ pct(record.metrics.mrr_at_5) }}
              </span>
            </template>
            <template v-else-if="column.key === 'passed'">{{ record.passed }} / {{ record.total }}</template>
            <template v-else-if="column.key === 'time'">{{ formatTime(record.finished_at) }}</template>
            <template v-else-if="column.key === 'action'">
              <a @click="viewRun(record)">查看结果</a>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <a-modal v-model:open="datasetModal" title="新建测试集" ok-text="创建" @ok="submitDataset">
      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="datasetForm.name" />
        </a-form-item>
        <div class="form-grid">
          <a-form-item label="品牌">
            <a-select v-model:value="datasetForm.brand_code" allow-clear>
              <a-select-option value="HP">HP</a-select-option>
              <a-select-option value="Canon">Canon</a-select-option>
              <a-select-option value="Epson">Epson</a-select-option>
              <a-select-option value="Brother">Brother</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="评测类型">
            <a-select v-model:value="datasetForm.category">
              <a-select-option value="retrieval">检索</a-select-option>
              <a-select-option value="diagnosis">诊断</a-select-option>
              <a-select-option value="safety">安全</a-select-option>
            </a-select>
          </a-form-item>
        </div>
        <a-form-item label="型号 ID">
          <a-input v-model:value="datasetForm.model_id" placeholder="hp_deskjet_2700_series" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="datasetForm.description" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="itemModal" title="添加测试问题" ok-text="添加" @ok="submitItem">
      <a-form layout="vertical">
        <a-form-item label="问题" required>
          <a-textarea v-model:value="itemForm.question" :rows="2" />
        </a-form-item>
        <a-form-item label="标准证据 doc_id（逗号分隔）">
          <a-input v-model:value="itemForm.expectedDocs" placeholder="rk_hp_paper, rk_hp_ink" />
        </a-form-item>
        <a-form-item label="期望故障类别">
          <a-input v-model:value="itemForm.expected_fault_category" placeholder="paper_feed" />
        </a-form-item>
        <a-form-item label="期望转人工">
          <a-checkbox v-model:checked="itemForm.expected_escalation" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="runModal" title="评测结果" width="820px" :footer="null">
      <div v-if="runDetail">
        <div class="metric-grid">
          <template v-for="(value, key) in runDetail.metrics" :key="key">
            <div v-if="key !== 'note'" class="metric">
              <div class="metric-label">{{ metricLabel(key) }}</div>
              <div class="metric-value">{{ formatMetric(value) }}</div>
            </div>
          </template>
        </div>
        <p v-if="runDetail.metrics.note" class="tiny" style="margin-top: 10px">
          {{ runDetail.metrics.note }}
        </p>
        <a-table :data-source="runDetail.results" :columns="resultColumns" :pagination="{ pageSize: 10 }" row-key="id" size="small" style="margin-top: 16px">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'recall'">
              <a-tag :color="record.recall5 ? 'green' : 'red'">{{ record.recall5 ? '命中' : '未命中' }}</a-tag>
            </template>
            <template v-else-if="column.key === 'fault'">
              {{ record.fault_category || '—' }}
              <a-tag v-if="record.fault_match" color="green" style="margin-left: 4px">一致</a-tag>
            </template>
            <template v-else-if="column.key === 'docs'">
              <span class="tiny">{{ (record.retrieved_doc_ids || []).join(', ') || '—' }}</span>
            </template>
          </template>
        </a-table>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  createDataset,
  createItem,
  deleteDataset,
  deleteItem,
  getRun,
  listDatasets,
  listItems,
  listRuns,
  runEvaluation,
} from '../../api/evaluation'

const datasetColumns = [
  { title: '数据集', key: 'name', dataIndex: 'name' },
  { title: '类型', dataIndex: 'category', width: 100 },
  { title: '题目数', dataIndex: 'item_count', width: 90 },
  { title: '创建时间', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 220 },
]
const itemColumns = [
  { title: '问题', dataIndex: 'question' },
  { title: '标准证据', key: 'expected' },
  { title: '期望分类', dataIndex: 'expected_fault_category', width: 110 },
  { title: '期望升级', key: 'escalation', width: 100 },
  { title: '操作', key: 'action', width: 70 },
]
const runColumns = [
  { title: '#', dataIndex: 'id', width: 60 },
  { title: '数据集', dataIndex: 'dataset_name' },
  { title: '状态', dataIndex: 'status', width: 90 },
  { title: '通过 / 总数', key: 'passed', width: 110 },
  { title: '指标摘要', key: 'metrics' },
  { title: '完成时间', key: 'time', width: 170 },
  { title: '操作', key: 'action', width: 90 },
]
const resultColumns = [
  { title: '问题', dataIndex: 'question' },
  { title: '命中', key: 'recall', width: 80 },
  { title: 'RR', dataIndex: 'reciprocal_rank', width: 60 },
  { title: '故障分类', key: 'fault', width: 130 },
  { title: '召回证据', key: 'docs' },
]

const datasets = ref([])
const items = ref([])
const runs = ref([])
const selected = ref(null)
const loading = ref(false)
const datasetModal = ref(false)
const itemModal = ref(false)
const runModal = ref(false)
const runDetail = ref(null)
const datasetForm = ref({ name: '', brand_code: undefined, model_id: '', category: 'retrieval', description: '' })
const itemForm = ref({ question: '', expectedDocs: '', expected_fault_category: '', expected_escalation: false })

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}
function pct(value) {
  return typeof value === 'number' ? value.toFixed(2) : '—'
}
function metricLabel(key) {
  return (
    {
      recall_at_5: 'Recall@5',
      mrr_at_5: 'MRR@5',
      fault_accuracy: '故障分类准确率',
      escalation_recall: '转人工召回率',
      avg_latency_ms: '平均耗时(ms)',
      items_with_expected_docs: '标准证据题数',
      note: '说明',
    }[key] || key
  )
}
function formatMetric(value) {
  return typeof value === 'number' ? value.toFixed(2) : value
}

async function load() {
  loading.value = true
  try {
    const res = await listDatasets()
    datasets.value = res.data
    await loadRuns()
  } finally {
    loading.value = false
  }
}

async function loadRuns() {
  const res = await listRuns()
  runs.value = res.data
}

async function selectDataset(record) {
  selected.value = record
  const res = await listItems(record.id)
  items.value = res.data
}

async function submitDataset() {
  if (!datasetForm.value.name) {
    message.warning('请填写数据集名称')
    return
  }
  try {
    await createDataset({
      ...datasetForm.value,
      model_id: datasetForm.value.model_id || null,
      brand_code: datasetForm.value.brand_code || null,
    })
    datasetModal.value = false
    message.success('已创建')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '创建失败')
  }
}

async function removeDataset(record) {
  await deleteDataset(record.id)
  if (selected.value?.id === record.id) selected.value = null
  await load()
}

async function submitItem() {
  if (!itemForm.value.question) return
  try {
    await createItem(selected.value.id, {
      question: itemForm.value.question,
      expected_doc_ids: itemForm.value.expectedDocs.split(',').map((item) => item.trim()).filter(Boolean),
      expected_fault_category: itemForm.value.expected_fault_category || null,
      expected_escalation: itemForm.value.expected_escalation,
    })
    itemModal.value = false
    itemForm.value = { question: '', expectedDocs: '', expected_fault_category: '', expected_escalation: false }
    await selectDataset(selected.value)
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '添加失败')
  }
}

async function removeItem(record) {
  await deleteItem(selected.value.id, record.id)
  await selectDataset(selected.value)
  await load()
}

async function run(record) {
  message.loading({ content: '正在运行评测…', key: 'eval' })
  try {
    const res = await runEvaluation(record.id)
    message.success({ content: '评测完成', key: 'eval' })
    runDetail.value = res.data
    runModal.value = true
    await loadRuns()
  } catch (err) {
    message.error({ content: err.response?.data?.detail || '评测失败', key: 'eval' })
  }
}

async function viewRun(record) {
  const res = await getRun(record.id)
  runDetail.value = res.data
  runModal.value = true
}

onMounted(load)
</script>

<style scoped>
.name-cell {
  font-weight: 600;
}
.danger-link {
  color: var(--color-danger);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
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
  word-break: break-word;
}
</style>