<template>
  <AppLayout>
    <div class="content-container">
      <a-card :title="isAdmin ? '知识库管理' : '知识库'">
        <template #extra>
          <a-input-search
            v-model:value="searchQuery"
            placeholder="搜索知识库..."
            style="width: 200px; margin-right: 12px"
            allow-clear
            @search="fetchKbs"
          />
          <template v-if="isAdmin">
            <a-button
              style="margin-right: 8px"
              @click="handleCleanup"
            >
              清理失效
            </a-button>
            <a-button
              type="primary"
              @click="openCreate"
            >
              新建知识库
            </a-button>
          </template>
        </template>

        <a-table
          :data-source="kbs"
          :columns="columns"
          :loading="loading"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button
                type="link"
                @click="openDocs(record)"
              >
                文档
              </a-button>
              <template v-if="isAdmin">
                <a-button
                  type="link"
                  @click="openEdit(record)"
                >
                  编辑
                </a-button>
                <a-popconfirm
                  title="确认删除？"
                  @confirm="handleDelete(record.id)"
                >
                  <a-button
                    type="link"
                    danger
                  >
                    删除
                  </a-button>
                </a-popconfirm>
              </template>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 新建知识库弹窗 -->
      <a-modal
        v-model:open="showCreate"
        title="新建知识库"
        @ok="handleCreate"
      >
        <a-form layout="vertical">
          <a-form-item
            label="名称"
            required
          >
            <a-input v-model:value="newKb.name" />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea v-model:value="newKb.description" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 编辑知识库弹窗 -->
      <a-modal
        v-model:open="showEdit"
        title="编辑知识库"
        @ok="handleUpdate"
      >
        <a-form layout="vertical">
          <a-form-item
            label="名称"
            required
          >
            <a-input v-model:value="editKb.name" />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea v-model:value="editKb.description" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 文档管理弹窗 -->
      <a-modal
        v-model:open="showDocs"
        :title="`文档管理 — ${currentKb.name}`"
        :footer="null"
        width="700px"
      >
        <div
          v-if="isAdmin"
          style="margin-bottom: 16px"
        >
          <a-upload
            :before-upload="handleBeforeUpload"
            :show-upload-list="false"
            accept=".pdf,.docx,.txt,.md"
          >
            <a-button
              type="primary"
              :loading="uploading"
            >
              上传文档
            </a-button>
          </a-upload>
          <span style="margin-left: 8px; color: #999; font-size: 12px">
            支持 PDF、DOCX、TXT、MD
          </span>
        </div>

        <a-table
          :data-source="docs"
          :columns="docColumns"
          :loading="docsLoading"
          row-key="id"
          size="small"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-popconfirm
                v-if="isAdmin"
                title="确认删除此文档？"
                @confirm="handleDeleteDoc(record.id)"
              >
                <a-button
                  type="link"
                  danger
                  size="small"
                >
                  删除
                </a-button>
              </a-popconfirm>
            </template>
          </template>
        </a-table>
      </a-modal>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'
import {
  listKnowledgeBases,
  createKnowledgeBase,
  updateKnowledgeBase,
  deleteKnowledgeBase,
  cleanupOrphanKnowledgeBases,
} from '../api/knowledge'
import { listDocuments, uploadDocument, deleteDocument } from '../api/documents'

const authStore = useAuthStore()

const isAdmin = computed(() => authStore.user?.is_admin)
const kbs = ref([])
const loading = ref(false)
const searchQuery = ref('')

const showCreate = ref(false)
const newKb = reactive({ name: '', description: '' })

const showEdit = ref(false)
const editKb = reactive({ id: null, name: '', description: '' })

const showDocs = ref(false)
const currentKb = reactive({ id: null, name: '' })
const docs = ref([])
const docsLoading = ref(false)
const uploading = ref(false)

const columns = computed(() => {
  const cols = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action', width: isAdmin.value ? 200 : 80 },
  ]
  return cols
})

const docColumns = [
  { title: '文件名', dataIndex: 'filename', key: 'filename' },
  { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80 },
  { title: '切片数', dataIndex: 'chunk_count', key: 'chunk_count', width: 80 },
  {
    title: '大小',
    dataIndex: 'file_size',
    key: 'file_size',
    width: 100,
    customRender: ({ text }) => {
      if (!text) return '-'
      if (text < 1024) return `${text} B`
      if (text < 1024 * 1024) return `${(text / 1024).toFixed(1)} KB`
      return `${(text / 1024 / 1024).toFixed(1)} MB`
    },
  },
  { title: '操作', key: 'action', width: 80 },
]

async function fetchKbs() {
  loading.value = true
  try {
    const res = await listKnowledgeBases(searchQuery.value || undefined)
    kbs.value = res.data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  newKb.name = ''
  newKb.description = ''
  showCreate.value = true
}

async function handleCreate() {
  if (!newKb.name.trim()) {
    message.warning('请输入名称')
    return
  }
  await createKnowledgeBase(newKb)
  message.success('创建成功')
  showCreate.value = false
  fetchKbs()
}

function openEdit(record) {
  editKb.id = record.id
  editKb.name = record.name
  editKb.description = record.description || ''
  showEdit.value = true
}

async function handleUpdate() {
  if (!editKb.name.trim()) {
    message.warning('请输入名称')
    return
  }
  await updateKnowledgeBase(editKb.id, {
    name: editKb.name,
    description: editKb.description,
  })
  message.success('更新成功')
  showEdit.value = false
  fetchKbs()
}

async function handleDelete(id) {
  await deleteKnowledgeBase(id)
  message.success('已删除')
  fetchKbs()
}

async function handleCleanup() {
  const res = await cleanupOrphanKnowledgeBases()
  if (res.data.count > 0) {
    message.success(`已清理 ${res.data.count} 个失效知识库`)
  } else {
    message.info('没有失效的知识库')
  }
  fetchKbs()
}

// 文档管理
async function openDocs(record) {
  currentKb.id = record.id
  currentKb.name = record.name
  showDocs.value = true
  await fetchDocs()
}

async function fetchDocs() {
  docsLoading.value = true
  try {
    const res = await listDocuments(currentKb.id)
    docs.value = res.data
  } finally {
    docsLoading.value = false
  }
}

async function handleBeforeUpload(file) {
  uploading.value = true
  try {
    await uploadDocument(currentKb.id, file)
    message.success(`${file.name} 上传成功`)
    fetchDocs()
  } catch (e) {
    message.error(`上传失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    uploading.value = false
  }
  return false // 阻止 a-upload 自动上传
}

async function handleDeleteDoc(docId) {
  await deleteDocument(docId)
  message.success('文档已删除')
  fetchDocs()
}

onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
})
</script>

<style scoped>
.main-content {
  flex: 1;
  background: #f7f7f8;
  overflow-y: auto;
  padding: 24px;
}

.content-container {
  max-width: 960px;
  margin: 0 auto;
}
</style>
