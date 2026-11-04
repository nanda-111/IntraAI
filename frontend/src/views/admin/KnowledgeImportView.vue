<template>
  <div class="page">
    <PageHeader title="文档导入与解析" subtitle="支持 PDF、DOCX、TXT、MD、HTML 与结构化 JSON/JSONL；导入后进入待审核状态，未审核内容不会参与检索。">
      <template #actions>
        <a-button @click="$router.push('/admin/knowledge/review')">去审核</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <div class="grid-2">
        <div class="panel">
          <div class="panel-title"><span>上传文件</span></div>
          <a-form layout="vertical">
            <a-form-item label="知识来源" required>
              <a-select v-model:value="form.source_id" placeholder="选择已登记来源">
                <a-select-option v-for="item in sources" :key="item.id" :value="item.id">
                  {{ item.title }}（{{ item.authority_level }} 级）
                </a-select-option>
              </a-select>
            </a-form-item>
            <div class="form-grid">
              <a-form-item label="品牌代码" required>
                <a-select v-model:value="form.brand_code" @change="onBrandChange">
                  <a-select-option v-for="brand in brands" :key="brand.brand_code" :value="brand.brand_code">
                    {{ brand.name }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="适用型号 / 系列" required>
                <a-select v-model:value="form.model_scope" show-search placeholder="选择型号或系列">
                  <a-select-option v-for="model in brandModels" :key="model.model_id" :value="model.model_id">
                    {{ model.name }}
                  </a-select-option>
                  <a-select-option v-for="series in seriesOptions" :key="series" :value="series">
                    系列：{{ series }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="故障类别">
                <a-select v-model:value="form.fault_category">
                  <a-select-option v-for="item in categories" :key="item.code" :value="item.code">{{ item.label }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="错误代码">
                <a-input v-model:value="form.fault_code" placeholder="如 E4，可留空" />
              </a-form-item>
              <a-form-item label="代码体系">
                <a-input v-model:value="form.code_system" placeholder="HP 错误代码/指示灯" />
              </a-form-item>
              <a-form-item label="风险等级">
                <a-select v-model:value="form.risk_level">
                  <a-select-option value="L1">L1 低风险</a-select-option>
                  <a-select-option value="L2">L2 谨慎操作</a-select-option>
                  <a-select-option value="L3">L3 高风险（不进入自助检索）</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="来源类型">
                <a-select v-model:value="form.source_type" allow-clear placeholder="默认跟随来源">
                  <a-select-option value="official">官方资料</a-select-option>
                  <a-select-option value="faq">官方 FAQ</a-select-option>
                  <a-select-option value="manual">人工整理</a-select-option>
                  <a-select-option value="community">社区案例</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="地区范围">
                <a-input v-model:value="form.region_scope" />
              </a-form-item>
            </div>
            <a-form-item label="文件">
              <a-upload
                v-model:file-list="fileList"
                :before-upload="beforeUpload"
                :max-count="1"
                accept=".pdf,.docx,.txt,.md,.html,.htm,.json,.jsonl"
              >
                <a-button><UploadOutlined /> 选择文件</a-button>
              </a-upload>
            </a-form-item>
            <a-button type="primary" :loading="uploading" :disabled="!fileList.length" @click="upload">
              开始导入
            </a-button>
          </a-form>
        </div>

        <div class="panel">
          <div class="panel-title"><span>导入说明</span></div>
          <div class="notice">
            <p><strong>结构化 JSON / JSONL</strong> 可以一次导入多条知识，字段包括 title、symptom、possible_causes、steps、safety_warnings 等，导入后仍需审核。</p>
            <p><strong>PDF / DOCX / TXT / MD</strong> 会按段落切片生成待审核草稿。原文片段默认没有结构化步骤，需要在审核页补充步骤后才能发布。</p>
            <p><strong>HTML 快照</strong> 会提取正文并切片；URL 只作为来源登记，不会作为唯一向量化文本。</p>
            <p>重复文件按来源与 checksum 自动跳过。</p>
          </div>
          <a-alert
            v-if="result"
            :type="result.parse_status === 'failed' ? 'error' : 'success'"
            show-icon
            :message="result.message || `已生成 ${result.created} 条待审核知识`"
          >
            <template v-if="result.items?.length" #description>
              <div v-for="item in result.items.slice(0, 6)" :key="item.doc_id" class="tiny">
                {{ item.title }} · {{ item.review_status }}
              </div>
            </template>
          </a-alert>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">
          <span>最近导入文档</span>
          <a-button size="small" @click="loadDocuments"><ReloadOutlined /> 刷新</a-button>
        </div>
        <a-table :data-source="documents" :columns="docColumns" :pagination="{ pageSize: 8 }" row-key="id" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="statusColor(record.parse_status)">{{ statusLabel(record.parse_status) }}</a-tag>
            </template>
            <template v-else-if="column.key === 'time'">{{ formatTime(record.created_at) }}</template>
          </template>
        </a-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, UploadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { getBrands, getFaultCategories, getModels } from '../../api/products'
import { importDocument, listSources, listDocuments } from '../../api/printerKnowledge'

const sources = ref([])
const brands = ref([])
const models = ref([])
const categories = ref([])
const documents = ref([])
const fileList = ref([])
const uploading = ref(false)
const result = ref(null)

const form = ref({
  source_id: undefined,
  brand_code: undefined,
  model_scope: undefined,
  region_scope: 'CN',
  fault_category: 'paper_feed',
  fault_code: '',
  code_system: '',
  risk_level: 'L1',
  source_type: undefined,
})

const docColumns = [
  { title: '文件', dataIndex: 'file_name' },
  { title: '来源 ID', dataIndex: 'source_id', width: 90 },
  { title: '解析状态', key: 'status', width: 110 },
  { title: '知识条数', dataIndex: 'chunk_count', width: 90 },
  { title: '导入时间', key: 'time', width: 180 },
]
const brandModels = computed(() => models.value.filter((item) => item.brand_code === form.value.brand_code))
const seriesOptions = computed(() => [...new Set(brandModels.value.map((item) => item.series))])

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}
function statusLabel(status) {
  return { pending: '待解析', parsing: '解析中', parsed: '已解析', failed: '解析失败' }[status] || status
}
function statusColor(status) {
  return { parsed: 'green', failed: 'red', parsing: 'processing' }[status] || 'default'
}

function beforeUpload(file) {
  fileList.value = [file]
  return false
}

async function upload() {
  if (!form.value.source_id || !form.value.brand_code || !form.value.model_scope) {
    message.warning('请选择来源、品牌和适用型号')
    return
  }
  const formData = new FormData()
  formData.append('file', fileList.value[0])
  Object.entries(form.value).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') formData.append(key, value)
  })
  uploading.value = true
  try {
    const res = await importDocument(formData)
    result.value = res.data
    if (res.data.parse_status === 'failed') message.error(res.data.message)
    else message.success(`导入完成，生成 ${res.data.created} 条待审核知识`)
    fileList.value = []
    await loadDocuments()
  } catch (err) {
    message.error(err.response?.data?.detail || '导入失败')
  } finally {
    uploading.value = false
  }
}

async function loadDocuments() {
  const res = await listDocuments()
  documents.value = res.data
}

function onBrandChange() {
  form.value.model_scope = undefined
}

onMounted(async () => {
  const [sourceRes, brandRes, categoryRes, modelRes] = await Promise.all([
    listSources(),
    getBrands(),
    getFaultCategories(),
    getModels(),
  ])
  sources.value = sourceRes.data
  brands.value = brandRes.data
  categories.value = categoryRes.data
  models.value = modelRes.data
  await loadDocuments()
})
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 14px;
}
.notice p {
  font-size: 13px;
  line-height: 1.75;
  color: var(--color-text-secondary);
  margin: 0 0 10px;
}
</style>