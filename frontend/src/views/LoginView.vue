<template>
  <div class="login-container">
    <div class="login-left">
      <div class="brand">
        <div class="brand-logo">
          AI
        </div>
        <h1 class="brand-name">
          IntraAI
        </h1>
        <p class="brand-tagline">
          企业级智能知识助手平台
        </p>
      </div>
      <div class="brand-features">
        <div class="feature-item">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <span>RAG 知识检索增强</span>
        </div>
        <div class="feature-item">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span>多轮对话上下文理解</span>
        </div>
        <div class="feature-item">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <rect
              x="3"
              y="3"
              width="18"
              height="18"
              rx="2"
            />
            <path d="M3 9h18" />
            <path d="M9 21V9" />
          </svg>
          <span>多格式文档智能解析</span>
        </div>
      </div>
    </div>

    <div class="login-right">
      <div class="login-card">
        <h2 class="login-title">
          {{ isLogin ? '欢迎回来' : '创建账号' }}
        </h2>
        <p class="login-subtitle">
          {{ isLogin ? '登录以继续使用' : '注册以开始使用 IntraAI' }}
        </p>

        <a-form
          :model="form"
          layout="vertical"
          class="login-form"
          @finish="handleSubmit"
        >
          <a-form-item
            label="用户名"
            name="username"
            :rules="[{ required: true, message: '请输入用户名' }]"
          >
            <a-input
              v-model:value="form.username"
              placeholder="请输入用户名"
              size="large"
            />
          </a-form-item>

          <a-form-item
            v-if="!isLogin"
            label="邮箱"
            name="email"
            :rules="[{ required: true, message: '请输入邮箱' }]"
          >
            <a-input
              v-model:value="form.email"
              placeholder="请输入邮箱"
              size="large"
            />
          </a-form-item>

          <a-form-item
            label="密码"
            name="password"
            :rules="[{ required: true, message: '请输入密码' }]"
          >
            <a-input-password
              v-model:value="form.password"
              placeholder="请输入密码"
              size="large"
            />
          </a-form-item>

          <a-form-item style="margin-top: 8px">
            <a-button
              type="primary"
              html-type="submit"
              :loading="loading"
              block
              size="large"
            >
              {{ isLogin ? '登录' : '注册' }}
            </a-button>
          </a-form-item>
        </a-form>

        <div class="login-footer">
          <a
            class="toggle-link"
            @click="isLogin = !isLogin"
          >
            {{ isLogin ? '没有账号？去注册' : '已有账号？去登录' }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isLogin = ref(true)
const loading = ref(false)
const form = reactive({
  username: '',
  email: '',
  password: '',
})

async function handleSubmit() {
  loading.value = true
  try {
    if (isLogin.value) {
      await authStore.login({ username: form.username, password: form.password })
      message.success('登录成功')
      router.push('/')
    } else {
      await authStore.register(form)
      message.success('注册成功，请登录')
      isLogin.value = true
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  min-height: 100vh;
}

/* Left panel */
.login-left {
  flex: 1;
  background: linear-gradient(135deg, #0f1017 0%, #1a1d3a 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px;
  position: relative;
  overflow: hidden;
}

.login-left::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at 30% 50%, rgba(77, 107, 254, 0.08) 0%, transparent 50%);
}

.brand {
  position: relative;
  z-index: 1;
  margin-bottom: 48px;
}

.brand-logo {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--color-primary), #7c5cfc);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 20px;
  box-shadow: 0 4px 24px rgba(77, 107, 254, 0.3);
}

.brand-name {
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px;
  letter-spacing: -0.5px;
}

.brand-tagline {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.brand-features {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

.feature-item svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  opacity: 0.6;
}

/* Right panel */
.login-right {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: var(--color-bg-elevated);
}

.login-card {
  width: 100%;
  max-width: 360px;
}

.login-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--color-text-tertiary);
  margin: 0 0 32px;
}

.login-form :deep(.ant-form-item-label > label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.login-footer {
  text-align: center;
  margin-top: 16px;
}

.toggle-link {
  font-size: 14px;
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: none;
  transition: color var(--transition-fast);
}

.toggle-link:hover {
  color: var(--color-primary-hover);
}

/* Responsive */
@media (max-width: 768px) {
  .login-left {
    display: none;
  }
  .login-right {
    width: 100%;
  }
}
</style>
