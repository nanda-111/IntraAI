<template>
  <div class="page">
    <PageHeader title="服务首页" :subtitle="greeting">
      <template #actions>
        <a-button @click="$router.push('/products')">选择设备</a-button>
        <a-button type="primary" @click="startDiagnosis">
          <ToolOutlined /> 开始故障排查
        </a-button>
      </template>
    </PageHeader>

    <div class="page-body">
      <section class="hero">
        <div class="hero-main">
          <div class="hero-kicker">当前设备</div>
          <template v-if="currentDevice">
            <h2 class="hero-title">{{ currentDevice.model?.name }}</h2>
            <div class="hero-meta">
              <a-tag :color="currentDevice.model?.support_status === 'active' ? 'green' : 'orange'">
                {{ currentDevice.model?.support_status_label }}
              </a-tag>
              <span>{{ currentDevice.model?.brand_name }} · {{ currentDevice.model?.region }}</span>
              <span v-if="currentDevice.model?.knowledge_coverage">
                已收录 {{ currentDevice.model.knowledge_coverage }} 条适用知识
              </span>
            </div>
            <div class="hero-actions">
              <a-button type="primary" @click="$router.push('/assistant')">
                <MessageOutlined /> 咨询智能客服
              </a-button>
              <a-button @click="$router.push('/knowledge')"><BookOutlined /> 查看资料</a-button>
              <a-button @click="$router.push(`/products/${currentDevice.model_id}`)">
                设备详情
              </a-button>
            </div>
          </template>
          <template v-else>
            <h2 class="hero-title">先添加你的打印机</h2>
            <p class="muted">
              确认品牌与具体型号后，平台才能提供对应型号的官方资料、错误码解释和诊断步骤。
            </p>
            <a-button type="primary" @click="$router.push('/products')">去添加设备</a-button>
          </template>
        </div>
        <div class="quick-grid">
          <router-link to="/assistant" class="quick-card">
            <MessageOutlined />
            <span class="quick-title">智能咨询</span>
            <span class="quick-sub">自由描述问题，获取带来源的回答</span>
          </router-link>
          <router-link to="/diagnosis" class="quick-card">
            <ToolOutlined />
            <span class="quick-title">故障排查</span>
            <span class="quick-sub">按步骤执行并反馈结果</span>
          </router-link>
          <router-link to="/knowledge" class="quick-card">
            <BookOutlined />
            <span class="quick-title">错误代码</span>
            <span class="quick-sub">按品牌和型号查询代码含义</span>
          </router-link>
          <router-link to="/tickets" class="quick-card">
            <FileTextOutlined />
            <span class="quick-title">提交工单</span>
            <span class="quick-sub">未解决时转人工处理</span>
          </router-link>
        </div>
      </section>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">进行中的诊断</div>
          <div class="stat-value">{{ activeDiagnoses }}</div>
          <div class="stat-hint">可继续未完成的排查</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">待处理工单</div>
          <div class="stat-value">{{ openTickets }}</div>
          <div class="stat-hint">提交后可在工单中心跟踪</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">历史诊断</div>
          <div class="stat-value">{{ diagnoses.length }}</div>
          <div class="stat-hint">包含已解决与已转人工</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平台支持型号</div>
          <div class="stat-value">{{ supportedCount }}</div>
          <div class="stat-hint">四品牌首期型号系列</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="panel">
          <div class="panel-title">
            <span>最近诊断</span>
            <router-link to="/history" class="link">全部记录</router-link>
          </div>
          <a-empty v-if="!diagnoses.length" description="还没有诊断记录" :image="simpleImage" />
          <div v-else class="record-list">
            <router-link
              v-for="item in diagnoses.slice(0, 4)"
              :key="item.id"
              :to="`/diagnosis/${item.id}`"
              class="record"
            >
              <div class="record-main">
                <span class="record-title">{{ item.model_name || '未确认型号' }}</span>
                <span class="tiny">{{ item.fault_category_label }} · {{ item.symptom || '暂无描述' }}</span>
              </div>
              <StatusTag kind="diagnosis" :status="item.status" />
            </router-link>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <span>工单状态</span>
            <router-link to="/tickets" class="link">工单中心</router-link>
          </div>
          <a-empty v-if="!tickets.length" description="暂无工单" :image="simpleImage" />
          <div v-else class="record-list">
            <router-link
              v-for="item in tickets.slice(0, 4)"
              :key="item.id"
              :to="`/tickets/${item.id}`"
              class="record"
            >
              <div class="record-main">
                <span class="record-title">{{ item.title }}</span>
                <span class="tiny">{{ item.ticket_no }} · {{ formatTime(item.created_at) }}</span>
              </div>
              <StatusTag kind="ticket" :status="item.status" :label="item.status_label" />
            </router-link>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <div class="panel">
          <div class="panel-title"><span>热门问题</span></div>
          <div class="question-list">
            <button
              v-for="question in suggestions"
              :key="question"
              class="question"
              @click="askQuestion(question)"
            >
              <QuestionCircleOutlined />
              <span>{{ question }}</span>
            </button>
          </div>
        </div>
        <div class="panel">
          <div class="panel-title">
            <span>平台支持型号</span>
            <router-link to="/products" class="link">型号中心</router-link>
          </div>
          <div class="brand-list">
            <div v-for="brand in brands" :key="brand.brand_code" class="brand-row">
              <div class="brand-mark">{{ brand.brand_code.slice(0, 2) }}</div>
              <div class="brand-info">
                <span>{{ brand.name }}</span>
                <span class="tiny">{{ brand.active_model_count }} / {{ brand.model_count }} 个型号已支持</span>
              </div>
              <a-tag>{{ brand.model_count }} 型号</a-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Empty } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import {
  BookOutlined,
  FileTextOutlined,
  MessageOutlined,
  QuestionCircleOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { getBrands, getDevices, getModels } from '../../api/products'
import { listDiagnoses } from '../../api/diagnosis'
import { getSuggestions } from '../../api/assistant'
import { listTickets } from '../../api/tickets'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const devices = ref([])
const diagnoses = ref([])
const tickets = ref([])
const brands = ref([])
const suggestions = ref([])
const supportedCount = ref(0)

const currentDevice = computed(() => devices.value.find((item) => item.is_current) || null)
const activeDiagnoses = computed(
  () =>
    diagnoses.value.filter(
      (item) => !['RESOLVED', 'CLOSED', 'CANCELLED', 'TICKET_OPEN'].includes(item.status),
    ).length,
)
const openTickets = computed(
  () => tickets.value.filter((item) => !['closed', 'resolved'].includes(item.status)).length,
)
const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = auth.user?.display_name || auth.user?.username || ''
  const prefix = hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'
  return `${prefix}${name ? `，${name}` : ''}。这里汇总你的设备与售后进度。`
})

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function startDiagnosis() {
  if (!currentDevice.value) {
    router.push('/products')
    return
  }
  router.push('/diagnosis')
}

function askQuestion(question) {
  router.push({ path: '/assistant', query: { q: question } })
}

onMounted(async () => {
  const results = await Promise.allSettled([
    getDevices(),
    listDiagnoses(),
    listTickets(),
    getBrands(),
    getModels({ status: 'active' }),
  ])
  if (results[0].status === 'fulfilled') devices.value = results[0].value.data
  if (results[1].status === 'fulfilled') diagnoses.value = results[1].value.data
  if (results[2].status === 'fulfilled') tickets.value = results[2].value.data
  if (results[3].status === 'fulfilled') brands.value = results[3].value.data
  if (results[4].status === 'fulfilled') supportedCount.value = results[4].value.data.length

  const modelId = currentDevice.value?.model_id
  getSuggestions(modelId)
    .then((res) => {
      suggestions.value = res.data.items.slice(0, 5)
    })
    .catch(() => {
      suggestions.value = []
    })
})
</script>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(320px, 1.25fr) minmax(300px, 1fr);
  gap: 18px;
}
.hero-main {
  background: linear-gradient(135deg, #101226 0%, #1c2250 55%, #29347a 100%);
  border-radius: var(--radius-lg);
  padding: 26px;
  color: #fff;
}
.hero-kicker {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.hero-title {
  font-size: 26px;
  font-weight: 700;
  margin: 8px 0 10px;
}
.hero-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
}
.hero-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.quick-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-decoration: none;
  color: var(--color-text-primary);
  font-size: 20px;
  transition: all var(--transition-fast);
}
.quick-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
.quick-title {
  font-size: 14px;
  font-weight: 650;
  margin-top: 4px;
}
.quick-sub {
  font-size: 12px;
  color: var(--color-text-tertiary);
  line-height: 1.5;
}
.link {
  font-size: 12.5px;
  color: var(--color-primary);
  text-decoration: none;
}
.record-list {
  display: flex;
  flex-direction: column;
}
.record {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-light);
  text-decoration: none;
  color: inherit;
}
.record:last-child {
  border-bottom: none;
}
.record-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.record-title {
  font-size: 13.5px;
  font-weight: 600;
}
.question-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.question {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 8px;
  border: none;
  background: none;
  border-radius: 8px;
  text-align: left;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.question:hover {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}
.brand-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
}
.brand-row:last-child {
  border-bottom: none;
}
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--color-bg-sunken);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-secondary);
}
.brand-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  font-size: 13px;
}
</style>