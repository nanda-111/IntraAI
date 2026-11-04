<template>
  <div class="page">
    <PageHeader title="维护与耗材指南" subtitle="只展示当前型号已核验的维护说明与耗材资料；未核验的料号不会推荐。" />

    <div class="page-body">
      <div class="filter-bar">
        <ModelSelect v-model="modelId" allow-all placeholder="选择型号查看维护资料" @change="load" />
        <a-radio-group v-model:value="tab" button-style="solid" @change="load">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="ink_supply">耗材与加墨</a-radio-button>
          <a-radio-button value="print_quality">清洁与打印质量</a-radio-button>
          <a-radio-button value="paper_feed">纸张与进纸</a-radio-button>
        </a-radio-group>
      </div>

      <a-alert
        type="info"
        show-icon
        message="耗材兼容性说明"
        description="耗材型号必须根据精确型号和地区资料核验。平台不会推荐未经核验的替代耗材或料号；请以官方资料为准。"
      />

      <a-spin :spinning="loading">
        <a-empty v-if="!items.length" :description="modelId ? '该型号暂无维护资料' : '请先选择型号'" />
        <div v-else class="maintenance-grid">
          <router-link
            v-for="item in items"
            :key="item.doc_id"
            :to="{ path: '/knowledge', query: { model_id: modelId || undefined, doc: item.doc_id } }"
            class="maintenance-card"
          >
            <div class="card-head">
              <span class="category">{{ item.fault_category_label }}</span>
              <span class="tiny">{{ item.model_scope }}</span>
            </div>
            <div class="card-title">{{ item.title }}</div>
            <div class="card-snippet">{{ item.snippet }}</div>
            <div class="card-foot">
              <span class="tiny">来源 {{ item.source?.authority_level }} · 更新 {{ formatTime(item.updated_at) }}</span>
              <ArrowRightOutlined />
            </div>
          </router-link>
        </div>
      </a-spin>

      <div class="panel tips">
        <div class="section-title">日常维护建议</div>
        <ul>
          <li>使用与型号匹配的纸张规格，避免受潮或过厚的纸张造成进纸异常。</li>
          <li>长时间不打印时，按官方建议定期打印测试页，减少喷嘴堵塞。</li>
          <li>清洁扫描玻璃和进纸滚轮时先断电，避免使用尖锐工具或直接喷水。</li>
          <li>加墨或更换耗材前核对型号与地区版本，保留官方资料中的操作顺序。</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowRightOutlined } from '@ant-design/icons-vue'
import PageHeader from '../../components/PageHeader.vue'
import ModelSelect from '../../components/ModelSelect.vue'
import { listKnowledge } from '../../api/printerKnowledge'

const items = ref([])
const modelId = ref('')
const tab = ref('')
const loading = ref(false)

function formatTime(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

async function load() {
  loading.value = true
  try {
    const params = { size: 50 }
    if (modelId.value) params.model_id = modelId.value
    if (tab.value) params.fault_category = tab.value
    const res = await listKnowledge(params)
    items.value = res.data.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.maintenance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.maintenance-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  text-decoration: none;
  color: inherit;
}
.maintenance-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.category {
  font-size: 11.5px;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border-radius: 4px;
  padding: 1px 6px;
}
.card-title {
  font-size: 14.5px;
  font-weight: 650;
}
.card-snippet {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}
.tips ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 2;
  color: var(--color-text-secondary);
}
</style>