<template>
  <div class="model-select">
    <a-select
      v-model:value="brand"
      :options="brandOptions"
      :placeholder="brandPlaceholder"
      style="width: 132px"
      allow-clear
      @change="handleBrandChange"
    />
    <a-select
      v-model:value="model"
      :options="modelOptions"
      :placeholder="placeholder"
      show-search
      option-filter-prop="label"
      style="min-width: 230px; flex: 1"
      :allow-clear="allowAll"
      @change="emitModel"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getBrands, getModels } from '../api/products'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '选择型号' },
  brandPlaceholder: { type: String, default: '品牌' },
  allowAll: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const brands = ref([])
const models = ref([])
const brand = ref(undefined)
const model = ref(props.modelValue || undefined)

const brandOptions = computed(() => [
  { value: '', label: '全部品牌' },
  ...brands.value.map((item) => ({ value: item.brand_code, label: item.name })),
])
const modelOptions = computed(() => {
  const options = models.value.map((item) => ({
    value: item.model_id,
    label: `${item.brand_code} · ${item.name}`,
  }))
  if (props.allowAll) return [{ value: '', label: '全部型号' }, ...options]
  return options
})

async function loadModels() {
  const params = {}
  if (brand.value) params.brand = brand.value
  const res = await getModels(params)
  models.value = res.data
  if (model.value && !models.value.some((item) => item.model_id === model.value)) {
    model.value = undefined
    emit('update:modelValue', '')
  }
}

function handleBrandChange() {
  model.value = undefined
  loadModels()
  if (props.allowAll) {
    emit('update:modelValue', '')
    emit('change', '')
  }
}

function emitModel(value) {
  emit('update:modelValue', value || '')
  emit('change', value || '')
}

watch(
  () => props.modelValue,
  (value) => {
    model.value = value || undefined
    if (value) {
      const found = models.value.find((item) => item.model_id === value)
      if (found) brand.value = found.brand_code
    }
  },
)

onMounted(async () => {
  const res = await getBrands()
  brands.value = res.data.filter((item) => item.status === 'active')
  if (props.allowAll) brand.value = ''
  await loadModels()
  if (props.modelValue) {
    const found = models.value.find((item) => item.model_id === props.modelValue)
    if (found) brand.value = found.brand_code
  }
})
</script>

<style scoped>
.model-select {
  display: flex;
  gap: 8px;
  width: 100%;
}
</style>