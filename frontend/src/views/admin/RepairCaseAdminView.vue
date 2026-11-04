<template>
  <div class="page">
    <PageHeader title="维修案例管理" subtitle="社区与人工案例只用于现象理解、分类和测试辅助，不直接作为型号专属官方维修步骤。">
      <template #actions>
        <a-button @click="importModal = true">导入案例</a-button>
        <a-button type="primary" @click="openModal()"><PlusOutlined /> 新建案例</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <a-alert
        type="warning"
        show-icon
        message="社区案例，不是官方维修步骤"
        description="型号未知的案例不会转化为具体型号结论；进入正式检索前必须由知识管理员整理并关联官方来源。"
      />

      <div class="filter-bar">
        <a-input v-model:value="filters.brand" placeholder="品牌" style="width: 130px" allow-clear @press-enter="load" />
        <a-select v-model:value="filters.model_known" style="width: 150px" allow-clear placeholder="型号是否明确" @change="load">
          <a-select-option value="known">型号明确</a-select-option>
          <a-select-option value="unknown">型号未知</a-select-option>
        </a-select>
        <a-select v-model:value="filters.fault_label" style="width: 160px" allow-clear placeholder="故障类别" @change="load">
          <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
        </a-select>
        <a-input-search v-model:value="filters.q" placeholder="搜索问题描述" style="width: 240px" @search="load" />
      </div>

      <a-spin :spinning="loading">
        <a-table :data-source="cases" :columns="columns" :pagination="{ pageSize: 10 }" row-key="case_id" size="middle">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'problem'">
              <div class="problem">{{ record.problem_text }}</div>
              <div class="tiny">{{ record.raw_brand }} · {{ record.raw_model || '型号未知' }}</div>
            </template>
            <template v-else-if="column.key === 'fault'">{{ record.fault_label_text }}</template>
            <template v-else-if="column.key === 'model_known'">
              <a-tag :color="record.model_known === 'known' ? 'blue' : 'default'">
                {{ record.model_known === 'known' ? '型号明确' : '型号未知' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a @click="openModal(record)">编辑</a>
                <a class="danger-link" @click="remove(record)">删除</a>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-spin>
    </div>

    <a-modal v-model:open="modal" :title="editing ? '编辑案例' : '新建案例'" width="600px" ok-text="保存" @ok="save">
      <a-form layout="vertical">
        <div class="form-grid">
          <a-form-item label="原始品牌">
            <a-input v-model:value="form.raw_brand" />
          </a-form-item>
          <a-form-item label="原始型号">
            <a-input v-model:value="form.raw_model" />
          </a-form-item>
          <a-form-item label="故障类别">
            <a-select v-model:value="form.fault_label" allow-clear>
              <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="型号是否明确">
            <a-select v-model:value="form.model_known">
              <a-select-option value="known">型号明确</a-select-option>
              <a-select-option value="unknown">型号未知</a-select-option>
            </a-select>
          </a-form-item>
        </div>
        <a-form-item label="问题描述" required>
          <a-textarea v-model:value="form.problem_text" :rows="3" />
        </a-form-item>
        <a-form-item label="维修结果">
          <a-textarea v-model:value="form.repair_outcome" :rows="2" />
        </a-form-item>
        <a-form-item label="可信度">
          <a-select v-model:value="form.credibility">
            <a-select-option value="community">社区记录</a-select-option>
            <a-select-option value="unverified">未验证</a-select-option>
            <a-select-option value="reviewed">人工复核</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="form.notes" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="importModal" title="导入案例（JSON / JSONL）" ok-text="上传" @ok="upload">
      <p class="muted">字段：raw_brand、raw_model、problem_text（必填）、fault_label、repair_outcome、model_known、credibility。</p>
      <a-upload v-model:file-list="fileList" :before-upload="() => false" :max-count="1" accept=".json,.jsonl">
        <a-button>选择文件</a-button>
      </a-upload>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { getFaultCategories } from '../../api/products'
import {
  createCase,
  deleteCase,
  importCases,
  listCases,
  updateCase,
} from '../../api/overview'

const columns = [
  { title: '问题描述', key: 'problem', dataIndex: 'problem_text' },
  { title: '故障类别', key: 'fault', width: 110 },
  { title: '型号', key: 'model_known', width: 100 },
  { title: '可信度', dataIndex: 'credibility', width: 100 },
  { title: '操作', key: 'action', width: 100 },
]
const cases = ref([])
const categories = ref([])
const filters = ref({ brand: '', model_known: undefined, fault_label: undefined, q: '' })
const loading = ref(false)
const modal = ref(false)
const importModal = ref(false)
const editing = ref(false)
const fileList = ref([])
const form = ref(empty())

function empty() {
  return {
    case_id: '',
    raw_brand: '',
    raw_model: '',
    problem_text: '',
    fault_label: undefined,
    repair_outcome: '',
    model_known: 'unknown',
    credibility: 'community',
    notes: '',
  }
}

async function load() {
  loading.value = true
  try {
    const params = {}
    Object.entries(filters.value).forEach(([key, value]) => {
      if (value) params[key] = value
    })
    const res = await listCases(params)
    cases.value = res.data
  } finally {
    loading.value = false
  }
}

function openModal(record) {
  editing.value = Boolean(record)
  form.value = record ? { ...record } : empty()
  modal.value = true
}

async function save() {
  if (!form.value.problem_text) {
    message.warning('请填写问题描述')
    return
  }
  try {
    if (editing.value) {
      await updateCase(form.value.case_id, form.value)
    } else {
      await createCase(form.value)
    }
    modal.value = false
    message.success('已保存')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '保存失败')
  }
}

async function remove(record) {
  try {
    await deleteCase(record.case_id)
    message.success('已删除')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '删除失败')
  }
}

async function upload() {
  if (!fileList.value.length) return
  const formData = new FormData()
  formData.append('file', fileList.value[0])
  try {
    const res = await importCases(formData)
    importModal.value = false
    fileList.value = []
    message.success(`已导入 ${res.data.created} 条案例`)
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '导入失败')
  }
}

onMounted(async () => {
  const res = await getFaultCategories()
  categories.value = res.data
  await load()
})
</script>

<style scoped>
.problem {
  font-size: 13px;
  line-height: 1.55;
}
.danger-link {
  color: var(--color-danger);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
</style>