<template>
  <div class="page">
    <PageHeader title="个人中心" subtitle="维护基本资料、当前设备和消息偏好；联系方式仅在创建工单时主动收集。" />

    <div class="page-body">
      <div class="grid-2">
        <div class="panel">
          <div class="panel-title"><span>基本资料</span></div>
          <a-form layout="vertical">
            <a-form-item label="用户名">
              <a-input :value="auth.user?.username" disabled />
            </a-form-item>
            <a-form-item label="显示名称">
              <a-input v-model:value="profile.display_name" placeholder="客服可见的称呼" />
            </a-form-item>
            <a-form-item label="邮箱">
              <a-input v-model:value="profile.email" />
            </a-form-item>
            <a-form-item label="联系电话">
              <a-input v-model:value="profile.phone" placeholder="可选，仅用于售后联系" />
            </a-form-item>
            <a-button type="primary" :loading="saving" @click="saveProfile">保存资料</a-button>
          </a-form>
        </div>

        <div class="panel">
          <div class="panel-title"><span>当前设备</span></div>
          <a-empty v-if="!devices.length" description="尚未添加设备">
            <a-button type="primary" @click="$router.push('/products')">去添加</a-button>
          </a-empty>
          <div v-else class="device-list">
            <div v-for="device in devices" :key="device.id" class="device">
              <div class="device-main">
                <div class="device-name">{{ device.model?.name }}</div>
                <div class="tiny">{{ device.model?.brand_name }} · {{ device.model?.series }}</div>
              </div>
              <a-tag v-if="device.is_current" color="green">当前设备</a-tag>
              <a-button v-else size="small" @click="makeCurrent(device.model_id)">设为当前</a-button>
              <a-button size="small" type="text" danger @click="remove(device.model_id)">移除</a-button>
            </div>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <div class="panel">
          <div class="panel-title"><span>修改密码</span></div>
          <a-form layout="vertical">
            <a-form-item label="原密码">
              <a-input-password v-model:value="password.old_password" />
            </a-form-item>
            <a-form-item label="新密码（至少 6 位）">
              <a-input-password v-model:value="password.new_password" />
            </a-form-item>
            <a-button @click="savePassword">更新密码</a-button>
          </a-form>
        </div>

        <div class="panel">
          <div class="panel-title"><span>数据与隐私</span></div>
          <ul class="privacy">
            <li>诊断记录、咨询会话和工单按账号隔离，其他用户无法查看。</li>
            <li>联系方式仅在你主动创建工单时收集，客服端默认脱敏展示。</li>
            <li>外部模型调用遵循最小必要原则，不发送与问题无关的个人信息。</li>
            <li>平台不连接打印机硬件，也不读取设备内部传感器。</li>
          </ul>
          <div class="divider-line" />
          <div class="account-row">
            <div>
              <div class="account-name">{{ auth.user?.username }}</div>
              <div class="tiny">角色：{{ roleLabel }}</div>
            </div>
            <a-button danger @click="logout">退出登录</a-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import PageHeader from '../../components/PageHeader.vue'
import { changePassword, getMe, updateMe } from '../../api/auth'
import { getDevices, removeDevice, setCurrentDevice } from '../../api/products'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const devices = ref([])
const saving = ref(false)
const profile = ref({ display_name: '', email: '', phone: '' })
const password = ref({ old_password: '', new_password: '' })

const roleLabel = computed(
  () =>
    ({
      user: '普通用户',
      agent: '客服人员',
      knowledge_admin: '知识库管理员',
      system_admin: '系统管理员',
    })[auth.role],
)

async function load() {
  const [meRes, deviceRes] = await Promise.all([getMe(), getDevices()])
  auth.user = meRes.data
  localStorage.setItem('user', JSON.stringify(meRes.data))
  profile.value = {
    display_name: meRes.data.display_name || '',
    email: meRes.data.email,
    phone: meRes.data.phone || '',
  }
  devices.value = deviceRes.data
}

async function saveProfile() {
  saving.value = true
  try {
    const res = await updateMe(profile.value)
    auth.user = res.data
    localStorage.setItem('user', JSON.stringify(res.data))
    message.success('资料已保存')
  } catch (err) {
    message.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  if (!password.value.old_password || !password.value.new_password) {
    message.warning('请填写原密码和新密码')
    return
  }
  try {
    await changePassword(password.value)
    message.success('密码已更新')
    password.value = { old_password: '', new_password: '' }
  } catch (err) {
    message.error(err.response?.data?.detail || '更新失败')
  }
}

async function makeCurrent(modelId) {
  await setCurrentDevice(modelId)
  const res = await getDevices()
  devices.value = res.data
}

async function remove(modelId) {
  await removeDevice(modelId)
  const res = await getDevices()
  devices.value = res.data
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(load)
</script>

<style scoped>
.device-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.device {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--color-border-light);
  border-radius: 9px;
  padding: 10px 12px;
}
.device-main {
  flex: 1;
}
.device-name {
  font-size: 13.5px;
  font-weight: 600;
}
.privacy {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.9;
  color: var(--color-text-secondary);
}
.account-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
}
.account-name {
  font-weight: 600;
}
</style>