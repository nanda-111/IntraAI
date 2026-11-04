<template>
  <div class="page">
    <PageHeader title="系统配置与日志" subtitle="查看模型/向量配置、索引状态和检索日志；密钥仅从环境变量读取，不在前端展示。">
      <template #actions>
        <a-button type="primary" :loading="reindexing" @click="reindex">重建知识索引</a-button>
        <a-button @click="load"><ReloadOutlined /> 刷新</a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <div v-if="settings" class="page-body">
        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>模型与检索配置</span></div>
            <div class="config-row"><span>LLM 服务地址</span><span>{{ settings.llm.base_url }}</span></div>
            <div class="config-row"><span>LLM 模型</span><span>{{ settings.llm.model }}</span></div>
            <div class="config-row">
              <span>API Key</span>
              <a-tag :color="settings.llm.api_key_configured ? 'green' : 'red'">
                {{ settings.llm.api_key_configured ? '已配置（环境变量）' : '未配置' }}
              </a-tag>
            </div>
            <div class="config-row"><span>Embedding 模型</span><span>{{ settings.embedding.model }}</span></div>
            <div class="config-row"><span>Reranker 模型</span><span>{{ settings.reranker.model }}</span></div>
            <div class="config-row"><span>上传目录</span><span>{{ settings.storage.upload_dir }}</span></div>
            <div class="config-row"><span>Chroma 目录</span><span>{{ settings.storage.chroma_dir }}</span></div>
          </div>

          <div class="panel">
            <div class="panel-title"><span>索引状态</span></div>
            <a-table :data-source="collectionRows" :columns="collectionColumns" :pagination="false" size="small" row-key="name">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'count'">
                  <a-tag :color="record.count > 0 ? 'green' : 'default'">{{ record.count }}</a-tag>
                </template>
              </template>
            </a-table>
            <a-alert
              type="info"
              show-icon
              style="margin-top: 12px"
              message="索引说明"
              description="知识发布时自动写入 Chroma；若索引为空，检索会自动回退到数据库关键词召回，仍可工作。批量导入后建议执行“重建知识索引”。"
            />
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <span>检索日志</span>
            <a-radio-group v-model:value="channel" size="small" @change="loadLogs">
              <a-radio-button value="">全部</a-radio-button>
              <a-radio-button value="assistant">智能客服</a-radio-button>
              <a-radio-button value="diagnosis">故障诊断</a-radio-button>
              <a-radio-button value="evaluation">评测</a-radio-button>
            </a-radio-group>
          </div>
          <a-table :data-source="logs" :columns="logColumns" :pagination="{ pageSize: 10 }" row-key="id" size="small">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'query'">
                <div class="query">{{ record.query }}</div>
                <div class="tiny">{{ record.model_id || '未绑定型号' }}</div>
              </template>
              <template v-else-if="column.key === 'candidates'">
                {{ record.vector_candidates }}/{{ record.bm25_candidates }}
              </template>
              <template v-else-if="column.key === 'time'">{{ formatTime(record.created_at) }}</template>
            </template>
          </a-table>
        </div>

        <div class="panel">
          <div class="panel-title"><span>合规与安全说明</span></div>
          <ul class="rules">
            <li>LLM 不直接执行 SQL、Python、Shell 或远程设备控制。</li>
            <li>维修步骤必须关联已审核知识 ID，模型不能生成无证据的型号专属步骤。</li>
            <li>用户联系方式最小化采集，客服端默认脱敏展示。</li>
            <li>日志记录型号过滤条件、召回证据 ID、工具调用和诊断状态，不记录不必要的敏感全文。</li>
          </ul>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import { getRetrievalLogs, getSettings } from '../../api/overview'
import { reindexKnowledge } from '../../api/printerKnowledge'

const settings = ref(null)
const logs = ref([])
const loading = ref(false)
const reindexing = ref(false)
const channel = ref('')

const collectionColumns = [
  { title: '集合', dataIndex: 'name' },
  { title: '文档数', key: 'count', width: 100 },
]
const logColumns = [
  { title: '查询', key: 'query', dataIndex: 'query' },
  { title: '渠道', dataIndex: 'channel', width: 100 },
  { title: '向量/BM25', key: 'candidates', width: 110 },
  { title: '证据', dataIndex: 'evidence_passed', width: 70 },
  { title: '耗时', dataIndex: 'latency_ms', width: 80 },
  { title: '时间', key: 'time', width: 170 },
]
const collectionRows = computed(() =>
  Object.entries(settings.value?.index_status || {}).map(([name, info]) => ({ name, ...info })),
)

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : ''
}

async function load() {
  loading.value = true
  try {
    const res = await getSettings()
    settings.value = res.data
    await loadLogs()
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  const params = { size: 20 }
  if (channel.value) params.channel = channel.value
  const res = await getRetrievalLogs(params)
  logs.value = res.data.items
}

async function reindex() {
  reindexing.value = true
  try {
    const res = await reindexKnowledge()
    message.success(`索引完成：${res.data.indexed}/${res.data.total}`)
    await load()
  } catch (err) {
    message.error(err.response?.data?.detail || '重建索引失败')
  } finally {
    reindexing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.config-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 13px;
}
.config-row:last-child {
  border-bottom: none;
}
.config-row > span:first-child {
  color: var(--color-text-tertiary);
}
.config-row > span:last-child {
  word-break: break-all;
  text-align: right;
}
.query {
  font-size: 12.5px;
}
.rules {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.9;
  color: var(--color-text-secondary);
}
</style>