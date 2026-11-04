<template>
  <div class="page">
    <PageHeader title="品牌与型号中心" subtitle="先确认品牌、系列和具体型号，再进入对应的帮助与诊断流程。">
      <template #actions>
        <a-button @click="load">
          <ReloadOutlined /> 刷新
        </a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="brand-grid">
        <button
          v-for="brand in brands"
          :key="brand.brand_code"
          class="brand-card"
          :class="{ active: brandFilter === brand.brand_code }"
          @click="selectBrand(brand.brand_code)"
        >
          <div class="brand-code">{{ brand.brand_code }}</div>
          <div class="brand-name">{{ brand.name }}</div>
          <div class="brand-count">{{ brand.active_model_count }} / {{ brand.model_count }} 个型号已支持</div>
        </button>
      </div>

      <div class="filter-bar">
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索型号、型号代码或别名，例如 2720"
          allow-clear
          style="width: 300px"
          @search="loadModels"
        />
        <a-select v-model:value="statusFilter" style="width: 150px" @change="loadModels">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option value="active">已支持</a-select-option>
          <a-select-option value="pilot">试运行</a-select-option>
        </a-select>
        <a-select v-model:value="brandFilter" style="width: 150px" @change="loadModels">
          <a-select-option value="">全部品牌</a-select-option>
          <a-select-option v-for="brand in brands" :key="brand.brand_code" :value="brand.brand_code">
            {{ brand.name }}
          </a-select-option>
        </a-select>
        <span class="muted">共 {{ models.length }} 个型号</span>
      </div>

      <a-spin :spinning="loading">
        <a-empty v-if="!models.length" description="没有匹配的型号" />
        <div v-else class="model-grid">
          <div v-for="model in models" :key="model.model_id" class="model-card">
            <div class="model-head">
              <div>
                <div class="model-brand">{{ model.brand_name }}</div>
                <div class="model-name">{{ model.name }}</div>
              </div>
              <StatusTag kind="model" :status="model.support_status" :label="model.support_status_label" />
            </div>
            <div class="model-tags">
              <a-tag v-for="feature in (model.supported_features || []).slice(0, 4)" :key="feature">
                {{ feature }}
              </a-tag>
            </div>
            <div class="model-meta">
              <span>{{ model.series }}</span>
              <span>知识 {{ model.knowledge_coverage }} 条</span>
            </div>
            <div class="model-actions">
              <a-button size="small" type="primary" ghost @click="openDetail(model.model_id)">
                查看详情
              </a-button>
              <a-button
                v-if="!isAdded(model.model_id)"
                size="small"
                @click="addToMyDevices(model.model_id)"
              >
                添加设备
              </a-button>
              <a-button
                v-else-if="!isCurrent(model.model_id)"
                size="small"
                @click="makeCurrent(model.model_id)"
              >
                设为当前
              </a-button>
              <a-tag v-else color="green">当前设备</a-tag>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <a-drawer
      v-model:open="drawerOpen"
      :width="560"
      title="型号详情"
      placement="right"
    >
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <div class="detail-head">
            <div>
              <div class="model-brand">{{ detail.brand_name }}</div>
              <h2 class="detail-name">{{ detail.name }}</h2>
              <div class="tiny">
                型号代码 {{ detail.model_code || '—' }} · {{ detail.series }} · {{ detail.region }}
              </div>
            </div>
            <StatusTag kind="model" :status="detail.support_status" :label="detail.support_status_label" />
          </div>

          <a-alert
            v-if="detail.support_status !== 'active'"
            type="warning"
            show-icon
            style="margin: 14px 0"
            message="该型号暂未开放型号专属自动诊断"
            description="仍可查看通用使用资料；如需维修指导，请提交售后工单。"
          />

          <div class="detail-section">
            <div class="section-title">支持的故障类别</div>
            <div class="cap-list">
              <div v-for="cap in detail.capabilities" :key="cap.id" class="cap-item">
                <span>{{ cap.fault_category_label }}</span>
                <a-tag :color="cap.verified_status === 'verified' ? 'green' : 'default'">
                  {{ cap.verified_status === 'verified' ? '已验证' : '待验证' }}
                </a-tag>
                <span class="tiny">{{ cap.code_system }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-title">常见错误代码</div>
            <div v-if="detail.error_codes?.length" class="code-list">
              <div v-for="code in detail.error_codes" :key="code.code" class="code-item">
                <span class="code">{{ code.code }}</span>
                <span>{{ code.label }}</span>
              </div>
            </div>
            <p v-else class="muted">该品牌暂未登记可展示的错误代码。</p>
          </div>

          <div class="detail-section">
            <div class="section-title">官方资料来源</div>
            <div v-if="detail.sources?.length" class="source-list">
              <a
                v-for="source in detail.sources"
                :key="source.source_key"
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
                class="source-row"
              >
                <span>{{ source.title }}</span>
                <span class="tiny">来源 {{ source.authority_level }} · v{{ source.version }}</span>
              </a>
            </div>
            <p v-else class="muted">尚未登记官方来源。</p>
          </div>

          <div class="detail-actions">
            <a-button type="primary" @click="$router.push(`/products/${detail.model_id}`)">
              完整型号页
            </a-button>
            <a-button v-if="!isAdded(detail.model_id)" @click="addToMyDevices(detail.model_id)">
              添加为我的设备
            </a-button>
            <a-button v-else-if="!isCurrent(detail.model_id)" @click="makeCurrent(detail.model_id)">
              设为当前设备
            </a-button>
          </div>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import {
  addDevice,
  getBrands,
  getDevices,
  getModel,
  getModels,
  setCurrentDevice,
} from '../../api/products'

const brands = ref([])
const models = ref([])
const devices = ref([])
const keyword = ref('')
const brandFilter = ref('')
const statusFilter = ref('')
const loading = ref(false)

const drawerOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

function isAdded(modelId) {
  return devices.value.some((item) => item.model_id === modelId)
}
function isCurrent(modelId) {
  return devices.value.some((item) => item.model_id === modelId && item.is_current)
}

async function load() {
  loading.value = true
  try {
    const [brandRes, deviceRes] = await Promise.all([getBrands(), getDevices()])
    brands.value = brandRes.data
    devices.value = deviceRes.data
    await loadModels()
  } finally {
    loading.value = false
  }
}

async function loadModels() {
  loading.value = true
  try {
    const params = {}
    if (brandFilter.value) params.brand = brandFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (keyword.value) params.q = keyword.value
    const res = await getModels(params)
    models.value = res.data
  } finally {
    loading.value = false
  }
}

function selectBrand(code) {
  brandFilter.value = brandFilter.value === code ? '' : code
  loadModels()
}

async function openDetail(modelId) {
  drawerOpen.value = true
  detailLoading.value = true
  try {
    const res = await getModel(modelId)
    detail.value = res.data
  } finally {
    detailLoading.value = false
  }
}

async function addToMyDevices(modelId) {
  try {
    await addDevice({ model_id: modelId, set_current: true })
    message.success('已添加为当前设备')
    const res = await getDevices()
    devices.value = res.data
  } catch (err) {
    message.error(err.response?.data?.detail || '添加失败')
  }
}

async function makeCurrent(modelId) {
  try {
    await setCurrentDevice(modelId)
    message.success('已切换当前设备')
    const res = await getDevices()
    devices.value = res.data
  } catch (err) {
    message.error(err.response?.data?.detail || '切换失败')
  }
}

onMounted(load)
</script>

<style scoped>
.brand-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}
.brand-card {
  text-align: left;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.brand-card:hover,
.brand-card.active {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
.brand-code {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--color-primary);
}
.brand-name {
  font-size: 16px;
  font-weight: 650;
  margin: 3px 0;
}
.brand-count {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.model-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.model-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.model-brand {
  font-size: 11.5px;
  color: var(--color-text-tertiary);
}
.model-name {
  font-size: 16px;
  font-weight: 650;
}
.model-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.model-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-tertiary);
}
.model-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: auto;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.detail-name {
  font-size: 20px;
  margin: 2px 0 4px;
}
.detail-section {
  margin-top: 20px;
}
.cap-list,
.code-list,
.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cap-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  font-size: 13px;
}
.code-item {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}
.code {
  font-family: var(--font-mono);
  background: var(--color-bg-sunken);
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 12px;
}
.source-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  text-decoration: none;
  color: var(--color-text-primary);
  font-size: 13px;
}
.source-row:hover {
  border-color: var(--color-primary);
}
.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
}
</style>