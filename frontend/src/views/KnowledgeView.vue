<template>
  <AppLayout>
    <div class="content-container">
      <div class="page-header">
        <div>
          <h2 class="page-title">
            {{ isAdmin ? '知识库管理' : '知识库' }}
          </h2>
          <p class="page-subtitle">
            管理和组织企业知识文档
          </p>
        </div>
        <div
          v-if="isAdmin"
          class="page-actions"
        >
          <a-input-search
            v-model:value="searchQuery"
            placeholder="搜索知识库..."
            style="width: 200px"
            allow-clear
            @search="fetchKbs"
          />
          <a-button
            :loading="syncing"
            @click="handleSync"
          >
            同步文件夹
          </a-button>
          <a-button @click="handleCleanup">
            清理失效
          </a-button>
          <a-button
            type="primary"
            @click="openCreate"
          >
            + 新建知识库
          </a-button>
        </div>
      </div>

      <a-table
        :data-source="kbs"
        :columns="columns"
        :loading="loading"
        row-key="id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="kb-name-cell">
              <div class="kb-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </div>
              <span>{{ record.name }}</span>
            </div>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="openDocs(record)"
              >
                文档
              </a-button>
              <template v-if="isAdmin">
                <a-button
                  type="link"
                  size="small"
                  @click="openEdit(record)"
                >
                  编辑
                </a-button>
                <a-popconfirm
                  title="确认删除此知识库？"
                  ok-text="删除"
                  cancel-text="取消"
                  @confirm="handleDelete(record.id)"
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
            </a-space>
          </template>
        </template>
      </a-table>

      <!-- Create modal -->
      <a-modal
        v-model:open="showCreate"
        title="新建知识库"
        ok-text="创建"
        cancel-text="取消"
        @ok="handleCreate"
      >
        <a-form layout="vertical">
          <a-form-item
            label="名称"
            required
          >
            <a-input
              v-model:value="newKb.name"
              placeholder="输入知识库名称"
            />
          </a-form-item>
          <a-form-item label="描述">
            <a-textarea
              v-model:value="newKb.description"
              placeholder="输入知识库描述（可选）"
              :rows="3"
            />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- Edit modal -->
      <a-modal
        v-model:open="showEdit"
        title="编辑知识库"
        ok-text="保存"
        cancel-text="取消"
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
            <a-textarea
              v-model:value="editKb.description"
              :rows="3"
            />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- Documents modal -->
      <a-modal
        v-model:open="showDocs"
        :title="`文档 — ${currentKb.name}`"
        :footer="null"
        width="700px"
      >
        <div
          v-if="isAdmin"
          class="doc-upload-area"
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
          <span class="upload-hint">支持 PDF、DOCX、TXT、MD</span>
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
            <template v-if="column.key === 'file_type'">
              <a-tag>{{ record.file_type.toUpperCase() }}</a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-popconfirm
                v-if="isAdmin"
                title="确认删除此文档？"
                ok-text="删除"
                cancel-text="取消"
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
  syncKnowledgeBases,
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
const syncing = ref(false)

const columns = computed(() => [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: isAdmin.value ? 200 : 80 },
])

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

async function handleSync() {
  syncing.value = true
  try {
    const res = await syncKnowledgeBases()
    const { created, updated, removed } = res.data
    const total = created + updated + removed
    if (total > 0) {
      const parts = []
      if (created > 0) parts.push(`新建 ${created}`)
      if (updated > 0) parts.push(`更新 ${updated}`)
      if (removed > 0) parts.push(`删除 ${removed}`)
      message.success(`同步完成：${parts.join('、')}`)
    } else {
      message.info('文件夹无变更，无需同步')
    }
    fetchKbs()
  } catch (e) {
    message.error(`同步失败: ${e.response?.data?.detail || e.message}`)
  } finally {
    syncing.value = false
  }
}

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
  return false
}

async function handleDeleteDoc(docId) {
  await deleteDocument(docId)
  message.success('文档已删除')
  fetchDocs()
}

onMounted(async () => {
  await authStore.fetchUser()
  if (authStore.user?.is_admin) {
    await handleSync()
  } else {
    fetchKbs()
  }
})
</script>

<style scoped>
.content-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 32px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 0;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* KB name cell */
.kb-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kb-icon {
  width: 32px;
  height: 32px;
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  flex-shrink: 0;
}

.kb-icon svg {
  width: 16px;
  height: 16px;
}

/* Doc upload area */
.doc-upload-area {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.upload-hint {
  font-size: 12px;
  color: var(--color-text-tertiary);
}
</style>
