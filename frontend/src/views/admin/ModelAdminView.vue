<template>
  <div class="page">
    <PageHeader title="品牌型号管理" subtitle="维护品牌、系列、具体型号、别名、地区版本、能力映射和支持状态。">
      <template #actions>
        <a-button v-if="tab === 'models'" type="primary" @click="openModelModal()">
          <PlusOutlined /> 新建型号
        </a-button>
        <a-button v-else type="primary" @click="openBrandModal()">
          <PlusOutlined /> 新建品牌
        </a-button>
      </template>
    </PageHeader>

    <a-tabs v-model:activeKey="tab">
      <a-tab-pane key="models" tab="型号管理">
        <div class="filter-bar" style="margin-bottom: 14px">
          <a-select v-model:value="filters.brand" style="width: 150px" allow-clear placeholder="全部品牌" @change="loadModels">
            <a-select-option v-for="item in brands" :key="item.brand_code" :value="item.brand_code">
              {{ item.name }}
            </a-select-option>
          </a-select>
          <a-select v-model:value="filters.status" style="width: 150px" allow-clear placeholder="全部状态" @change="loadModels">
            <a-select-option v-for="(label, value) in statusLabels" :key="value" :value="value">{{ label }}</a-select-option>
          </a-select>
          <a-input-search v-model:value="filters.q" placeholder="搜索型号" style="width: 240px" @search="loadModels" />
        </div>

        <a-spin :spinning="loading">
          <a-table :data-source="models" :columns="modelColumns" :pagination="{ pageSize: 10 }" row-key="model_id" size="middle">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <div class="name-cell">{{ record.name }}</div>
                <div class="tiny">{{ record.model_id }}</div>
              </template>
              <template v-else-if="column.key === 'status'">
                <StatusTag kind="model" :status="record.support_status" :label="record.support_status_label" />
              </template>
              <template v-else-if="column.key === 'coverage'">
                <div>{{ record.knowledge_coverage }} 条知识</div>
                <div class="tiny">{{ record.capabilities.length }} 类能力</div>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a @click="openModelModal(record)">编辑</a>
                  <a @click="openCapabilities(record)">能力</a>
                  <a class="danger-link" @click="removeModel(record)">删除</a>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>

      <a-tab-pane key="brands" tab="品牌管理">
        <a-spin :spinning="loading">
          <a-table :data-source="brands" :columns="brandColumns" :pagination="false" row-key="brand_code" size="middle">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'active' ? 'green' : 'default'">
                  {{ record.status === 'active' ? '启用' : '停用' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <a @click="openBrandModal(record)">编辑</a>
              </template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="modelModal" :title="modelForm.editing ? '编辑型号' : '新建型号'" width="640px" ok-text="保存" @ok="saveModel">
      <a-form layout="vertical">
        <div class="form-grid">
          <a-form-item label="品牌" required>
            <a-select v-model:value="modelForm.brand_code" :disabled="modelForm.editing">
              <a-select-option v-for="item in brands" :key="item.brand_code" :value="item.brand_code">{{ item.name }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="型号 ID" required>
            <a-input v-model:value="modelForm.model_id" :disabled="modelForm.editing" placeholder="hp_deskjet_2720" />
          </a-form-item>
          <a-form-item label="显示名称" required>
            <a-input v-model:value="modelForm.name" placeholder="HP DeskJet 2720" />
          </a-form-item>
          <a-form-item label="系列" required>
            <a-input v-model:value="modelForm.series" placeholder="DeskJet 2700 Series" />
          </a-form-item>
          <a-form-item label="型号代码">
            <a-input v-model:value="modelForm.model_code" />
          </a-form-item>
          <a-form-item label="地区">
            <a-input v-model:value="modelForm.region" />
          </a-form-item>
          <a-form-item label="支持状态">
            <a-select v-model:value="modelForm.support_status">
              <a-select-option v-for="(label, value) in statusLabels" :key="value" :value="value">{{ label }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="打印技术">
            <a-input v-model:value="modelForm.technology" />
          </a-form-item>
        </div>
        <a-form-item label="型号别名（逗号分隔）">
          <a-input v-model:value="modelForm.aliasesText" placeholder="DJ2720, HP2720, 惠普2720" />
        </a-form-item>
        <a-form-item label="支持功能（逗号分隔）">
          <a-input v-model:value="modelForm.featuresText" placeholder="打印, 复印, 扫描, Wi-Fi" />
        </a-form-item>
        <a-form-item label="发布说明">
          <a-textarea v-model:value="modelForm.release_note" :rows="2" />
        </a-form-item>
        <a-alert
          v-if="modelForm.support_status === 'active'"
          type="info"
          show-icon
          message="启用为“已支持”需要通过门槛校验"
          description="至少一条已验证能力、一条已发布知识、一个已登记官方来源，否则保存会被拒绝。"
        />
      </a-form>
    </a-modal>

    <a-modal v-model:open="brandModal" :title="brandForm.editing ? '编辑品牌' : '新建品牌'" ok-text="保存" @ok="saveBrand">
      <a-form layout="vertical">
        <a-form-item label="品牌代码" required>
          <a-input v-model:value="brandForm.brand_code" :disabled="brandForm.editing" placeholder="HP" />
        </a-form-item>
        <a-form-item label="品牌名称" required>
          <a-input v-model:value="brandForm.name" placeholder="惠普 HP" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="brandForm.status">
            <a-select-option value="active">启用</a-select-option>
            <a-select-option value="inactive">停用</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="brandForm.description" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer v-model:open="capDrawer" :width="620" title="型号能力映射">
      <template v-if="capModel">
        <div class="cap-head">
          <div>
            <div class="name-cell">{{ capModel.name }}</div>
            <div class="tiny">{{ capModel.model_id }}</div>
          </div>
          <a-tag>{{ capModel.capabilities.length }} 类</a-tag>
        </div>
        <div v-for="cap in capModel.capabilities" :key="cap.id" class="cap-row">
          <div class="cap-main">
            <div>{{ cap.fault_category_label }}</div>
            <div class="tiny">{{ cap.code_system || '未设置代码体系' }}</div>
          </div>
          <a-select
            :value="cap.verified_status"
            size="small"
            style="width: 110px"
            @change="(value) => updateCapability(cap, value)"
          >
            <a-select-option value="verified">已验证</a-select-option>
            <a-select-option value="pending">待验证</a-select-option>
          </a-select>
          <a-button size="small" type="text" danger @click="removeCapability(cap)">删除</a-button>
        </div>
        <div class="divider-line" />
        <div class="section-title">新增能力</div>
        <a-form layout="vertical">
          <a-form-item label="故障类别">
            <a-select v-model:value="capForm.fault_category">
              <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="代码体系">
            <a-input v-model:value="capForm.code_system" placeholder="HP 错误代码/指示灯" />
          </a-form-item>
          <a-form-item label="验证状态">
            <a-select v-model:value="capForm.verified_status">
              <a-select-option value="verified">已验证</a-select-option>
              <a-select-option value="pending">待验证</a-select-option>
            </a-select>
          </a-form-item>
          <a-button type="primary" @click="addCapability">添加能力</a-button>
        </a-form>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import {
  adminAddCapability,
  adminCreateBrand,
  adminCreateModel,
  adminDeleteCapability,
  adminDeleteModel,
  adminListBrands,
  adminUpdateBrand,
  adminUpdateCapability,
  adminUpdateModel,
  getFaultCategories,
  getModels,
} from '../../api/products'

const statusLabels = {
  planned: '规划中',
  building: '资料建设中',
  pilot: '试运行',
  active: '已支持',
  suspended: '暂停服务',
}
const modelColumns = [
  { title: '型号', key: 'name', dataIndex: 'name' },
  { title: '品牌 / 系列', key: 'series', dataIndex: 'series' },
  { title: '状态', key: 'status', width: 110 },
  { title: '知识覆盖', key: 'coverage', width: 130 },
  { title: '操作', key: 'action', width: 160 },
]
const brandColumns = [
  { title: '代码', dataIndex: 'brand_code', width: 110 },
  { title: '名称', dataIndex: 'name' },
  { title: '型号数', dataIndex: 'model_count', width: 90 },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'action', width: 80 },
]

const tab = ref('models')
const brands = ref([])
const models = ref([])
const categories = ref([])
const filters = ref({ brand: undefined, status: undefined, q: '' })
const loading = ref(false)

const modelModal = ref(false)
const modelForm = ref(emptyModel())
const brandModal = ref(false)
const brandForm = ref(emptyBrand())
const capDrawer = ref(false)
const capModel = ref(null)
const capForm = ref({ fault_category: 'paper_feed', code_system: '', verified_status: 'verified' })

function emptyModel() {
  return {
    editing: false,
    model_id: '',
    brand_code: undefined,
    name: '',
    series: '',
    model_code: '',
    region: 'CN',
    technology: 'inkjet',
    support_status: 'planned',
    aliasesText: '',
    featuresText: '',
    release_note: '',
  }
}
function emptyBrand() {
  return { editing: false, brand_code: '', name: '', status: 'active', description: '' }
}

function errorText(err) {
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.issues) return `${detail.message}：${detail.issues.join('；')}`
  return '操作失败'
}

async function loadBrands() {
  const res = await adminListBrands()
  brands.value = res.data
}
async function loadModels() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.brand) params.brand = filters.value.brand
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.q) params.q = filters.value.q
    const res = await getModels(params)
    models.value = res.data
  } finally {
    loading.value = false
  }
}

function openModelModal(record) {
  if (record) {
    modelForm.value = {
      editing: true,
      model_id: record.model_id,
      brand_code: record.brand_code,
      name: record.name,
      series: record.series,
      model_code: record.model_code || '',
      region: record.region,
      technology: record.technology,
      support_status: record.support_status,
      aliasesText: (record.aliases || []).join(', '),
      featuresText: (record.supported_features || []).join(', '),
      release_note: record.release_note || '',
    }
  } else {
    modelForm.value = emptyModel()
  }
  modelModal.value = true
}

async function saveModel() {
  const form = modelForm.value
  const payload = {
    name: form.name,
    series: form.series,
    model_code: form.model_code || null,
    region: form.region,
    technology: form.technology,
    support_status: form.support_status,
    aliases: form.aliasesText.split(',').map((item) => item.trim()).filter(Boolean),
    supported_features: form.featuresText.split(',').map((item) => item.trim()).filter(Boolean),
    release_note: form.release_note || null,
  }
  try {
    if (form.editing) {
      await adminUpdateModel(form.model_id, payload)
    } else {
      const res = await adminCreateModel({
        ...payload,
        model_id: form.model_id,
        brand_code: form.brand_code,
      })
      if (res.data.warning) {
        message.warning(`${res.data.warning}：${(res.data.issues || []).join('；')}`)
      }
    }
    modelModal.value = false
    message.success('已保存')
    await Promise.all([loadModels(), loadBrands()])
  } catch (err) {
    message.error(errorText(err))
  }
}

async function removeModel(record) {
  try {
    await adminDeleteModel(record.model_id)
    message.success('已删除')
    await loadModels()
  } catch (err) {
    message.error(errorText(err))
  }
}

function openBrandModal(record) {
  brandForm.value = record
    ? { editing: true, brand_code: record.brand_code, name: record.name, status: record.status, description: record.description }
    : emptyBrand()
  brandModal.value = true
}

async function saveBrand() {
  const form = brandForm.value
  try {
    if (form.editing) {
      await adminUpdateBrand(
        brands.value.find((item) => item.brand_code === form.brand_code).id,
        { name: form.name, status: form.status, description: form.description },
      )
    } else {
      await adminCreateBrand({
        brand_code: form.brand_code,
        name: form.name,
        status: form.status,
        description: form.description,
      })
    }
    brandModal.value = false
    message.success('已保存')
    await loadBrands()
  } catch (err) {
    message.error(errorText(err))
  }
}

async function openCapabilities(record) {
  capDrawer.value = true
  const res = await getModels({ q: record.model_id })
  capModel.value = res.data.find((item) => item.model_id === record.model_id) || record
  capForm.value.code_system = record.capabilities?.[0]?.code_system || ''
}

async function addCapability() {
  try {
    await adminAddCapability(capModel.value.model_id, {
      fault_category: capForm.value.fault_category,
      code_system: capForm.value.code_system || null,
      verified_status: capForm.value.verified_status,
      supported_features: [],
    })
    message.success('能力已添加')
    await openCapabilities(capModel.value)
    await loadModels()
  } catch (err) {
    message.error(errorText(err))
  }
}

async function updateCapability(cap, value) {
  try {
    await adminUpdateCapability(cap.id, { verified_status: value })
    await openCapabilities(capModel.value)
  } catch (err) {
    message.error(errorText(err))
  }
}

async function removeCapability(cap) {
  try {
    await adminDeleteCapability(cap.id)
    await openCapabilities(capModel.value)
    await loadModels()
  } catch (err) {
    message.error(errorText(err))
  }
}

onMounted(async () => {
  const [categoryRes] = await Promise.all([getFaultCategories(), loadBrands()])
  categories.value = categoryRes.data
  await loadModels()
})
</script>

<style scoped>
.name-cell {
  font-weight: 600;
  font-size: 13.5px;
}
.danger-link {
  color: var(--color-danger);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
.cap-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}
.cap-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-light);
}
.cap-main {
  flex: 1;
  font-size: 13px;
}
</style>