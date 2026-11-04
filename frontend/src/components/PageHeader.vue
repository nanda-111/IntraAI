<template>
  <div class="page-header">
    <div class="head-main">
      <button v-if="back" class="back-btn" @click="$router.back()">
        <ArrowLeftOutlined />
      </button>
      <div>
        <h1 class="title">{{ title }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div class="head-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
import { ArrowLeftOutlined } from '@ant-design/icons-vue'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  back: { type: Boolean, default: false },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.head-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.3px;
}
.subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.back-btn {
  border: 1px solid var(--color-border);
  background: var(--color-bg-elevated);
  width: 30px;
  height: 30px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 3px;
}
.back-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
</style>