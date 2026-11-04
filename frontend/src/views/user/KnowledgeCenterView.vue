<template>
  <div class="page">
    <PageHeader title="知识中心" subtitle="只展示已审核并发布的型号专属资料，可按品牌、型号、故障类别和错误代码筛选。" />

    <div class="page-body">
      <div class="filter-bar">
        <ModelSelect v-model="modelId" allow-all placeholder="选择型号" @change="load" />
        <a-select v-model:value="category" style="width: 170px" allow-clear placeholder="故障类别" @change="load">
          <a-select-option v-for="item in categories" :key="item.code" :value="item.code">
            {{ item.label }}
          </a-select-option>
        </a-select>
        <a-input
          v-model:value="faultCode"
          placeholder="错误代码，如 E4"
          style="width: 150px"
          allow-clear
          @press-enter="load"
        />
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索现象或标题"
          style="width: 240px"
          allow-clear
          @search="load"
        />
        <span class="muted">共 {{ total }} 条</span>
      </div>

      <a-spin :spinning="loading">
        <a-empty v-if="!items.length" description="没有匹配的已发布知识" />
        <div v-else class="knowledge-grid">
          <button v-for="item in items" :key="item.doc_id" class="knowledge-card" @click="openDetail(item)">
            <div class="card-head">
              <span class="category">{{ item.fault_category_label }}</span>
              <span class="tiny">{{ item.brand_code }} · {{ item.model_scope }}</span>
            </div>
            <div class="card-title">{{ item.title }}</div>
            <div class="card-snippet">{{ item.snippet }}</div>
            <div class="card-foot">
              <span class="tiny">来源 {{ item.source?.authority_level }} · v{{ item.version }}</span>
              <span v-if="item.fault_code" class="code">{{ item.fault_code }}</span>
            </div>
          </button>
        </div>

        <div v-if="total > pageSize" class="pager">
          <a-pagination
            v-model:current="page"
            :total="total"
            :page-size="pageSize"
            :show-size-changer="false"
            @change="load"
          />
        </div>
      </a-spin>
    </div>

    <a-drawer v-model:open="drawerOpen" :width="620" title="知识详情" placement="right">
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <div class="detail-title">{{ detail.title }}</div>
          <div class="detail-tags">
            <a-tag color="blue">{{ detail.fault_category_label }}</a-tag>
            <a-tag v-if="detail.fault_code">{{ detail.fault_code }}</a-tag>
            <a-tag>来源 {{ detail.source?.authority_level }}</a-tag>
            <StatusTag kind="risk" :status="detail.risk_level" />
          </div>
          <div class="detail-scope">
            适用型号：{{ detail.model_scope }} · 地区：{{ detail.region_scope }} · 版本：{{ detail.version }}
          </div>

          <section class="detail-section">
            <h4>故障现象</h4>
            <p>{{ detail.symptom || '—' }}</p>
          </section>
          <section v-if="detail.possible_causes?.length" class="detail-section">
            <h4>可能原因</h4>
            <ul>
              <li v-for="cause in detail.possible_causes" :key="cause">{{ cause }}</li>
            </ul>
          </section>
          <section v-if="detail.preconditions?.length" class="detail-section">
            <h4>前置条件</h4>
            <ul>
              <li v-for="item in detail.preconditions" :key="item">{{ item }}</li>
            </ul>
          </section>
          <section class="detail-section">
            <h4>操作步骤</h4>
            <div class="steps">
              <div v-for="(step, index) in detail.steps" :key="index" class="step">
                <span class="step-no">{{ index + 1 }}</span>
                <div>
                  <div>{{ step.instruction }}</div>
                  <div class="tiny">
                    <StatusTag kind="risk" :status="step.risk_level" />
                    <span v-if="step.expected_result"> 预期：{{ step.expected_result }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
          <section v-if="detail.expected_result" class="detail-section">
            <h4>预期结果</h4>
            <p>{{ detail.expected_result }}</p>
          </section>
          <section v-if="detail.verification_method" class="detail-section">
            <h4>验证方法</h4>
            <p>{{ detail.verification_method }}</p>
          </section>
          <a-alert
            v-if="detail.safety_warnings?.length"
            type="warning"
            show-icon
            class="detail-section"
            message="安全提示"
            :description="detail.safety_warnings.join('；')"
          />
          <section v-if="detail.source" class="detail-section">
            <h4>资料来源</h4>
            <a :href="detail.source.url" target="_blank" rel="noopener noreferrer">
              {{ detail.source.title }}
            </a>
            <div class="tiny">来源 {{ detail.source.authority_level }} 级 · 更新于 {{ formatTime(detail.updated_at) }}</div>
          </section>

          <div class="feedback-row">
            <span class="muted">这条资料有帮助吗？</span>
            <a-button size="small" @click="feedback(true)">有帮助</a-button>
            <a-button size="small" @click="feedback(false)">未解决</a-button>
          </div>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute } from 'vue-router'
import PageHeader from '../../components/PageHeader.vue'
import ModelSelect from '../../components/ModelSelect.vue'
import StatusTag from '../../components/StatusTag.vue'
import { getFaultCategories } from '../../api/products'
import { listKnowledge, getKnowledge } from '../../api/printerKnowledge'
import { submitFeedback } from '../../api/assistant'

const route = useRoute()
const items = ref([])
const categories = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const modelId = ref(route.query.model_id || '')
const category = ref(undefined)
const faultCode = ref('')
const keyword = ref('')

const drawerOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

function formatTime(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, size: pageSize }
    if (modelId.value) params.model_id = modelId.value
    if (category.value) params.fault_category = category.value
    if (faultCode.value) params.fault_code = faultCode.value.toUpperCase()
    if (keyword.value) params.q = keyword.value
    const res = await listKnowledge(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function openDetail(item) {
  drawerOpen.value = true
  detailLoading.value = true
  try {
    const res = await getKnowledge(item.doc_id)
    detail.value = res.data
  } finally {
    detailLoading.value = false
  }
}

async function feedback(resolved) {
  try {
    await submitFeedback({
      channel: 'knowledge',
      reference_id: detail.value?.id,
      rating: resolved ? 5 : 2,
      resolved,
      comment: resolved ? '资料有帮助' : '资料未解决问题',
    })
    message.success('感谢反馈')
  } catch {
    message.error('反馈提交失败')
  }
}

onMounted(async () => {
  const res = await getFaultCategories()
  categories.value = res.data
  await load()
  const doc = route.query.doc
  if (doc) {
    openDetail({ doc_id: doc })
  }
})
</script>

<style scoped>
.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 14px;
}
.knowledge-card {
  text-align: left;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.knowledge-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}
.category {
  font-size: 11.5px;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border-radius: 4px;
  padding: 1px 6px;
}
.card-title {
  font-size: 14.5px;
  font-weight: 650;
  line-height: 1.45;
}
.card-snippet {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.code {
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--color-bg-sunken);
  border-radius: 4px;
  padding: 1px 6px;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
.detail-title {
  font-size: 19px;
  font-weight: 700;
  line-height: 1.4;
}
.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 10px 0 6px;
}
.detail-scope {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.detail-section {
  margin-top: 18px;
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
.steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step {
  display: flex;
  gap: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: 9px;
  padding: 10px 12px;
  font-size: 13px;
}
.step-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.feedback-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border-light);
}
</style>