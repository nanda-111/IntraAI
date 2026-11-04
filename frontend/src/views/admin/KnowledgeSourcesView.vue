<template>
  <div class="page">
    <PageHeader title="知识来源管理" subtitle="登记官方手册、支持网页、授权数据和人工资料，保留 URL、权威等级、版本与许可说明。">
      <template #actions>
        <a-button type="primary" @click="openModal()"><PlusOutlined /> 登记来源</a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <a-spin :spinning="loading">
        <a-table :data-source="sources" :columns="columns" :pagination="{ pageSize: 10 }" row-key="id" size="middle">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <div class="title-cell">{{ record.title }}</div>
              <a v-if="record.url" :href="record.url" target="_blank" rel="noopener noreferrer" class="tiny">
                {{ record.url }}
              </a>
              <span v-else class="tiny">未登记 URL</span>
            </template>
            <template v-else-if="column.key === 'authority'">
              <a-tag :color="record.authority_level === 'A' ? 'blue' : 'default'">
                {{ record.authority_level }} 级
              </a-tag>
            </template>
            <template v-else-if="column.key === 'scope'">
              <div>{{ record.brand_code || '通用' }} · {{ record.region_scope }}</div>
              <div class="tiny">{{ record.model_scope || '不限型号' }}</div>
            </template>
            <template v-else-if="column.key === 'usage'">
              <div>{{ record.document_count }} 份文档</div>
              <div class="tiny">{{ record.knowledge_count }} 条知识</div>
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

    <a-modal v-model:open="modal" :title="editing ? '编辑来源' : '登记知识来源'" width="620px" ok-text="保存" @ok="save">
      <a-form layout="vertical">
        <div class="form-grid">
          <a-form-item label="来源标识">
            <a-input v-model:value="form.source_key" :disabled="editing" placeholder="留空自动生成" />
          </a-form-item>
          <a-form-item label="来源类型">
            <a-select v-model:value="form.source_type">
              <a-select-option value="official">官方资料</a-select-option>
              <a-select-option value="faq">官方 FAQ</a-select-option>
              <a-select-option value="manual">人工整理</a-select-option>
              <a-select-option value="community">社区案例</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="权威等级">
            <a-select v-model:value="form.authority_level">
              <a-select-option value="A">A · 官方资料</a-select-option>
              <a-select-option value="B">B · 社区数据</a-select-option>
              <a-select-option value="C">C · 人工审核知识</a-select-option>
              <a-select-option value="D">D · 评测数据</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="版本">
            <a-input v-model:value="form.version" />
          </a-form-item>
          <a-form-item label="品牌代码">
            <a-input v-model:value="form.brand_code" placeholder="HP / Canon / Epson / Brother" />
          </a-form-item>
          <a-form-item label="地区范围">
            <a-input v-model:value="form.region_scope" />
          </a-form-item>
        </div>
        <a-form-item label="标题" required>
          <a-input v-model:value="form.title" placeholder="HP DeskJet 2700 官方故障指示灯资料" />
        </a-form-item>
        <a-form-item label="URL">
          <a-input v-model:value="form.url" placeholder="https://..." />
        </a-form-item>
        <a-form-item label="适用型号范围">
          <a-input v-model:value="form.model_scope" placeholder="DeskJet 2700 Series" />
        </a-form-item>
        <a-form-item label="许可说明">
          <a-textarea v-model:value="form.license_note" :rows="2" placeholder="仅用于对应官方页面声明的型号和故障范围" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { createSource, deleteSource, listSources, updateSource } from '../../api/printerKnowledge'

const columns = [
  { title: '来源', key: 'title', dataIndex: 'title' },
  { title: '类型 / 等级', dataIndex: 'source_type', width: 90 },
  { title: '范围', key: 'scope', width: 200 },
  { title: '使用情况', key: 'usage', width: 110 },
  { title: '版本', dataIndex: 'version', width: 80 },
  { title: '操作', key: 'action', width: 100 },
]
const sources = ref([])
const loading = ref(false)
const modal = ref(false)
const editing = ref(false)
const form = ref(empty())

function empty() {
  return {
    source_key: '',
    title: '',
    url: '',
    source_type: 'official',
    authority_level: 'A',
    brand_code: '',
    model_scope: '',
    region_scope: 'CN',
    version: '1.0',
    license_note: '',
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listSources()
    sources.value = res.data
  } finally {
    loading.value = false
  }
}

function openModal(record) {
  editing.value = Boolean(record)
  form.value = record
    ? { ...record, source_key: record.source_key }
    : empty()
  modal.value = true
}

async function save() {
  if (!form.value.title) {
    message.warning('请填写来源标题')
    return
  }
  try {
    if (editing.value) {
      await updateSource(sources.value.find((item) => item.source_key === form.value.source_key).id, form.value)
    } else {
      await createSource(form.value)
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
    await deleteSource(record.id)
    message.success('已删除')
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.title-cell {
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
a.tiny {
  color: var(--color-primary);
}
</style>