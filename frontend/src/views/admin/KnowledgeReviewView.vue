<template>
  <div class="page">
    <PageHeader title="知识审核与发布" subtitle="审核型号范围、故障类型、代码体系、操作步骤、安全提示和来源证据；未审核知识不进入正式检索。">
      <template #actions>
        <a-button @click="$router.push('/admin/knowledge/import')">导入文档</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="filter-bar">
        <a-select v-model:value="filters.status" style="width: 140px" allow-clear placeholder="全部状态" @change="load">
          <a-select-option value="pending">待审核</a-select-option>
          <a-select-option value="approved">已通过</a-select-option>
          <a-select-option value="published">已发布</a-select-option>
          <a-select-option value="rejected">已退回</a-select-option>
          <a-select-option value="archived">已下架</a-select-option>
        </a-select>
        <a-select v-model:value="filters.brand" style="width: 140px" allow-clear placeholder="全部品牌" @change="load">
          <a-select-option value="HP">HP</a-select-option>
          <a-select-option value="Canon">Canon</a-select-option>
          <a-select-option value="Epson">Epson</a-select-option>
          <a-select-option value="Brother">Brother</a-select-option>
        </a-select>
        <a-select v-model:value="filters.fault_category" style="width: 160px" allow-clear placeholder="故障类别" @change="load">
          <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
        </a-select>
        <a-input-search v-model:value="filters.q" placeholder="搜索标题或现象" style="width: 240px" @search="load" />
        <span class="muted">共 {{ total }} 条</span>
      </div>

      <a-spin :spinning="loading">
        <a-table :data-source="items" :columns="columns" :pagination="{ pageSize: 12 }" row-key="doc_id" size="middle">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <div class="title-cell">{{ record.title }}</div>
              <div class="tiny">{{ record.model_scope }} · {{ record.fault_category_label }}</div>
            </template>
            <template v-else-if="column.key === 'authority'">
              <a-tag>{{ record.authority_level }} 级</a-tag>
              <div class="tiny">{{ record.source_type }}</div>
            </template>
            <template v-else-if="column.key === 'status'">
              <StatusTag kind="review" :status="record.review_status" />
            </template>
            <template v-else-if="column.key === 'time'">{{ formatTime(record.updated_at) }}</template>
            <template v-else-if="column.key === 'action'">
              <a @click="openDetail(record.doc_id)">审核</a>
            </template>
          </template>
        </a-table>
      </a-spin>
    </div>

    <a-drawer v-model:open="drawerOpen" :width="680" title="知识审核" placement="right">
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <div class="detail-head">
            <div>
              <div class="detail-title">{{ detail.title }}</div>
              <div class="tiny">{{ detail.doc_id }}</div>
            </div>
            <StatusTag kind="review" :status="detail.review_status" />
          </div>

          <template v-if="!editing">
            <div class="meta-grid">
              <div><span class="muted">品牌</span><div>{{ detail.brand_code }}</div></div>
              <div><span class="muted">适用范围</span><div>{{ detail.model_scope }}</div></div>
              <div><span class="muted">故障类别</span><div>{{ detail.fault_category_label }}</div></div>
              <div><span class="muted">代码</span><div>{{ detail.fault_code || '—' }}</div></div>
              <div><span class="muted">风险等级</span><StatusTag kind="risk" :status="detail.risk_level" /></div>
              <div><span class="muted">来源</span><div>{{ detail.source?.title || '未关联' }}</div></div>
            </div>

            <div class="detail-section">
              <h4>故障现象</h4>
              <p>{{ detail.symptom || '—' }}</p>
            </div>
            <div v-if="detail.possible_causes?.length" class="detail-section">
              <h4>可能原因</h4>
              <ul><li v-for="cause in detail.possible_causes" :key="cause">{{ cause }}</li></ul>
            </div>
            <div class="detail-section">
              <h4>操作步骤</h4>
              <a-empty v-if="!detail.steps?.length" description="缺少结构化步骤，不能发布" :image="simpleImage" />
              <div v-for="(step, index) in detail.steps" :key="index" class="step">
                <span class="step-no">{{ index + 1 }}</span>
                <div>
                  <div>{{ step.instruction }}</div>
                  <div class="tiny"><StatusTag kind="risk" :status="step.risk_level" /> {{ step.expected_result }}</div>
                </div>
              </div>
            </div>
            <div class="detail-section">
              <h4>安全提示</h4>
              <ul v-if="detail.safety_warnings?.length">
                <li v-for="warning in detail.safety_warnings" :key="warning">{{ warning }}</li>
              </ul>
              <p v-else class="warn-text">缺少安全提示，不能发布。</p>
            </div>

            <a-input v-model:value="reviewNote" placeholder="审核意见（退回/下架时必填说明）" style="margin: 16px 0" />
            <div class="review-actions">
              <a-button @click="onEditClick">编辑内容</a-button>
              <a-button type="primary" ghost @click="action('approve')">审核通过</a-button>
              <a-button danger @click="action('reject')">退回</a-button>
              <a-button type="primary" @click="action('publish')">发布并索引</a-button>
              <a-button @click="action('archive')">下架</a-button>
            </div>
          </template>

          <template v-else>
            <a-form layout="vertical">
              <a-form-item label="标题">
                <a-input v-model:value="editForm.title" />
              </a-form-item>
              <div class="form-grid">
                <a-form-item label="故障类别">
                  <a-select v-model:value="editForm.fault_category">
                    <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="错误代码">
                  <a-input v-model:value="editForm.fault_code" />
                </a-form-item>
                <a-form-item label="风险等级">
                  <a-select v-model:value="editForm.risk_level">
                    <a-select-option value="L1">L1</a-select-option>
                    <a-select-option value="L2">L2</a-select-option>
                    <a-select-option value="L3">L3（不发布）</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="版本">
                  <a-input v-model:value="editForm.version" />
                </a-form-item>
              </div>
              <a-form-item label="故障现象">
                <a-textarea v-model:value="editForm.symptom" :rows="3" />
              </a-form-item>
              <a-form-item label="可能原因（每行一条）">
                <a-textarea v-model:value="editForm.causesText" :rows="2" />
              </a-form-item>
              <a-form-item label="操作步骤（JSON 数组）">
                <a-textarea v-model:value="editForm.stepsText" :rows="8" class="mono" />
              </a-form-item>
              <a-form-item label="安全提示（每行一条）">
                <a-textarea v-model:value="editForm.warningsText" :rows="3" />
              </a-form-item>
              <a-form-item label="预期结果">
                <a-input v-model:value="editForm.expected_result" />
              </a-form-item>
              <a-form-item label="验证方法">
                <a-input v-model:value="editForm.verification_method" />
              </a-form-item>
              <div class="review-actions">
                <a-button @click="editing = false">取消</a-button>
                <a-button type="primary" @click="saveEdit">保存修改</a-button>
              </div>
            </a-form>
          </template>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import {
  adminGetKnowledge,
  adminListKnowledge,
  adminUpdateKnowledge,
  reviewKnowledge,
} from '../../api/printerKnowledge'
import { getFaultCategories } from '../../api/products'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const columns = [
  { title: '知识条目', key: 'title', dataIndex: 'title' },
  { title: '来源', key: 'authority', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '更新时间', key: 'time', width: 170 },
  { title: '操作', key: 'action', width: 70 },
]
const items = ref([])
const total = ref(0)
const categories = ref([])
const loading = ref(false)
const filters = ref({ status: 'pending', brand: undefined, fault_category: undefined, q: '' })

const drawerOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const editing = ref(false)
const reviewNote = ref('')
const editForm = ref({})

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

async function load() {
  loading.value = true
  try {
    const params = { size: 100 }
    Object.entries(filters.value).forEach(([key, value]) => {
      if (value) params[key] = value
    })
    const res = await adminListKnowledge(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function openDetail(docId) {
  drawerOpen.value = true
  editing.value = false
  detailLoading.value = true
  reviewNote.value = ''
  try {
    const res = await adminGetKnowledge(docId)
    detail.value = res.data
  } finally {
    detailLoading.value = false
  }
}

async function action(type) {
  try {
    const res = await reviewKnowledge(detail.value.doc_id, { action: type, note: reviewNote.value || null })
    detail.value = res.data
    message.success('操作成功')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '操作失败')
  }
}

function startEdit() {
  editForm.value = {
    title: detail.value.title,
    fault_category: detail.value.fault_category,
    fault_code: detail.value.fault_code || '',
    risk_level: detail.value.risk_level,
    version: detail.value.version,
    symptom: detail.value.symptom || '',
    causesText: (detail.value.possible_causes || []).join('\n'),
    stepsText: JSON.stringify(detail.value.steps || [], null, 2),
    warningsText: (detail.value.safety_warnings || []).join('\n'),
    expected_result: detail.value.expected_result || '',
    verification_method: detail.value.verification_method || '',
  }
}
// 点击“编辑内容”时初始化表单
function onEditClick() {
  startEdit()
  editing.value = true
}

async function saveEdit() {
  let steps
  try {
    steps = JSON.parse(editForm.value.stepsText || '[]')
  } catch {
    message.error('步骤 JSON 格式不正确')
    return
  }
  try {
    const res = await adminUpdateKnowledge(detail.value.doc_id, {
      title: editForm.value.title,
      fault_category: editForm.value.fault_category,
      fault_code: editForm.value.fault_code || null,
      risk_level: editForm.value.risk_level,
      version: editForm.value.version,
      symptom: editForm.value.symptom,
      possible_causes: editForm.value.causesText.split('\n').filter(Boolean),
      steps,
      safety_warnings: editForm.value.warningsText.split('\n').filter(Boolean),
      expected_result: editForm.value.expected_result,
      verification_method: editForm.value.verification_method,
    })
    detail.value = res.data
    editing.value = false
    message.success('已保存')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '保存失败')
  }
}

onMounted(async () => {
  const res = await getFaultCategories()
  categories.value = res.data
  await load()
})
</script>

<style scoped>
.title-cell {
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
  line-height: 1.45;
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
  font-size: 13px;
}
.detail-section {
  margin-top: 16px;
}
.detail-section h4 {
  font-size: 13.5px;
  margin: 0 0 6px;
}
.detail-section p,
.detail-section li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}
.detail-section ul {
  margin: 0;
  padding-left: 18px;
}
.step {
  display: flex;
  gap: 9px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  padding: 9px 11px;
  margin-bottom: 7px;
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
.warn-text {
  color: var(--color-danger);
  font-size: 13px;
}
.review-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
.mono :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>