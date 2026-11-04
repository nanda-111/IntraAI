<template>
  <div class="page">
    <PageHeader :title="detail?.name || '型号详情'" :subtitle="detail ? `${detail.brand_name} · ${detail.series} · ${detail.region}` : '加载中…'" back>
      <template #actions>
        <a-button @click="$router.push('/products')">返回型号中心</a-button>
        <a-button v-if="detail && !isAdded" @click="handleAdd">
          <PlusOutlined /> 添加为我的设备
        </a-button>
        <a-button type="primary" :disabled="detail?.support_status !== 'active'" @click="startDiagnosis">
          <ToolOutlined /> 开始诊断
        </a-button>
      </template>
    </PageHeader>

    <a-spin :spinning="loading">
      <div v-if="detail" class="page-body">
        <div class="overview panel">
          <div class="overview-main">
            <div class="overview-row">
              <StatusTag kind="model" :status="detail.support_status" :label="detail.support_status_label" />
              <a-tag v-for="feature in detail.supported_features" :key="feature">{{ feature }}</a-tag>
            </div>
            <p class="muted" style="margin-top: 8px">
              型号代码：{{ detail.model_code || '—' }} · 已收录 {{ detail.knowledge_coverage }} 条适用知识 · {{ detail.capabilities.length }} 类已验证故障
            </p>
            <a-alert
              v-if="detail.support_status !== 'active'"
              type="warning"
              show-icon
              style="margin-top: 12px"
              message="该型号暂不开放自动诊断"
              description="型号资料尚未达到发布门槛，仅提供通用信息查询。"
            />
          </div>
          <a-button type="primary" ghost @click="$router.push('/assistant')">
            <MessageOutlined /> 咨询客服
          </a-button>
        </div>

        <div class="grid-2">
          <div class="panel">
            <div class="panel-title"><span>故障类别</span></div>
            <div class="cap-grid">
              <div v-for="cap in detail.capabilities" :key="cap.id" class="cap-card">
                <span class="cap-label">{{ cap.fault_category_label }}</span>
                <a-tag :color="cap.verified_status === 'verified' ? 'green' : 'default'">
                  {{ cap.verified_status === 'verified' ? '已验证' : '待验证' }}
                </a-tag>
                <span class="tiny">{{ cap.code_system }}</span>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-title"><span>错误代码</span></div>
            <div v-if="detail.error_codes?.length" class="code-grid">
              <div v-for="code in detail.error_codes" :key="code.code" class="code-row">
                <span class="code">{{ code.code }}</span>
                <div>
                  <div>{{ code.label }}</div>
                  <div class="tiny">{{ code.category }}</div>
                </div>
              </div>
            </div>
            <a-empty v-else description="暂无登记错误代码" />
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <span>适用知识</span>
            <router-link :to="{ path: '/knowledge', query: { model_id: detail.model_id } }" class="link">
              在知识中心查看
            </router-link>
          </div>
          <a-empty v-if="!knowledge.length" description="暂无已发布知识" />
          <div v-else class="knowledge-grid">
            <router-link
              v-for="item in knowledge"
              :key="item.doc_id"
              :to="{ path: '/knowledge', query: { doc: item.doc_id } }"
              class="knowledge-item"
            >
              <span class="category">{{ item.fault_category_label }}</span>
              <span class="k-title">{{ item.title }}</span>
              <span class="tiny">{{ item.snippet }}</span>
            </router-link>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title"><span>官方资料来源</span></div>
          <a-empty v-if="!detail.sources?.length" description="尚未登记来源" />
          <div v-else class="source-rows">
            <a
              v-for="source in detail.sources"
              :key="source.source_key"
              :href="source.url"
              target="_blank"
              rel="noopener noreferrer"
              class="source-row"
            >
              <span>{{ source.title }}</span>
              <span class="tiny">来源 {{ source.authority_level }} · {{ source.source_type }} · v{{ source.version }}</span>
            </a>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { MessageOutlined, PlusOutlined, ToolOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { addDevice, getDevices, getModel } from '../../api/products'
import { listKnowledge } from '../../api/printerKnowledge'

const route = useRoute()
const router = useRouter()
const detail = ref(null)
const knowledge = ref([])
const devices = ref([])
const loading = ref(false)
const isAdded = computed(() => devices.value.some((item) => item.model_id === route.params.id))

async function load() {
  loading.value = true
  try {
    const [modelRes, deviceRes, knowledgeRes] = await Promise.all([
      getModel(route.params.id),
      getDevices(),
      listKnowledge({ model_id: route.params.id, size: 30 }),
    ])
    detail.value = modelRes.data
    devices.value = deviceRes.data
    knowledge.value = knowledgeRes.data.items
  } catch (err) {
    message.error(err.response?.data?.detail || '型号加载失败')
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  try {
    await addDevice({ model_id: route.params.id, set_current: true })
    message.success('已添加为当前设备')
    const res = await getDevices()
    devices.value = res.data
  } catch (err) {
    message.error(err.response?.data?.detail || '添加失败')
  }
}

function startDiagnosis() {
  router.push({ path: '/diagnosis', query: { model_id: route.params.id } })
}

onMounted(load)
</script>

<style scoped>
.overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.overview-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.cap-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.cap-card {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 13px;
}
.cap-label {
  font-weight: 600;
  flex: 1;
}
.code-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 230px;
  overflow-y: auto;
}
.code-row {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}
.code {
  font-family: var(--font-mono);
  background: var(--color-bg-sunken);
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 12px;
  min-width: 54px;
  text-align: center;
}
.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}
.knowledge-item {
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-decoration: none;
  color: inherit;
}
.knowledge-item:hover {
  border-color: var(--color-primary);
}
.category {
  font-size: 11px;
  color: var(--color-primary);
}
.k-title {
  font-size: 13.5px;
  font-weight: 600;
}
.source-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.source-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  padding: 9px 12px;
  text-decoration: none;
  color: inherit;
  font-size: 13px;
}
.source-row:hover {
  border-color: var(--color-primary);
}
.link {
  font-size: 12.5px;
  color: var(--color-primary);
  text-decoration: none;
}
</style>