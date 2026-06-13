/**
 * 认证状态管理 Store
 *
 * 【什么是 Pinia？为什么用它？】
 * Pinia 是 Vue 3 官方推荐的状态管理库（替代 Vuex），特点：
 * - 更简洁的 API，无需 mutations 和 modules 等复杂概念
 * - 天然支持 TypeScript
 * - 支持组合式 API 风格（和 <script setup> 一致）
 * - 支持服务端渲染（SSR）
 *
 * 【defineStore 的工作原理】
 * defineStore 是 Pinia 的核心函数，用于定义一个 Store。
 * - 第一个参数：store 的唯一标识（字符串），Pinia 用它来标识和访问同一个 store
 * - 第二个参数：setup 函数（组合式 API 风格），返回该 store 暴露的状态和方法
 *
 * 【组合式 API 风格 vs 选项式 API 风格】
 * Pinia 支持两种定义方式：
 * 1. 选项式：defineStore('auth', { state: () => ({...}), actions: {...} })
 * 2. 组合式：defineStore('auth', () => { const state = ref(...); return { state } })
 * 本项目选择组合式风格，与 Vue 3 的 <script setup> 保持一致，更自然。
 *
 * 【ref vs reactive 的区别】
 * - ref：可用于任何类型的值（基本类型、对象），读写需要 .value，模板中自动解包
 * - reactive：只能用于对象类型，自动深层响应式，不需要 .value
 * 这里用 ref 是因为：
 * 1. token 是字符串（基本类型），ref 是唯一选择
 * 2. user 虽然是对象，但整体替换而非属性修改，ref 更合适
 * 3. Pinia 的组合式风格中 ref 更常用、更一致
 *
 * 【为什么 token 要存到 localStorage？】
 * - 浏览器刷新后，JavaScript 变量会被重置（页面重新加载）
 * - localStorage 是浏览器提供的持久化存储，刷新页面不会丢失
 * - 这样用户刷新页面后仍保持登录状态，无需重新登录
 * - 注意：localStorage 是明文存储，生产环境建议使用 HttpOnly Cookie 方案
 *
 * 【在组件中如何使用这个 Store？】
 * 示例：
 *   import { useAuthStore } from '@/stores/auth'
 *   const authStore = useAuthStore()
 *   // 读取状态
 *   console.log(authStore.token)
 *   console.log(authStore.user)
 *   // 调用方法
 *   await authStore.login({ username: 'test', password: '123' })
 *   authStore.logout()
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi, getMe } from '../api/auth'

// 定义 auth store，使用组合式 API 风格（setup function）
export const useAuthStore = defineStore('auth', () => {
  // --- 状态 ---

  /**
   * JWT token（访问令牌）
   * 从 localStorage 恢复：如果用户之前登录过，刷新页面后仍能恢复登录状态
   * '' 表示未登录
   */
  const token = ref(localStorage.getItem('token') || '')

  /**
   * 当前登录用户信息
   * null 表示尚未获取用户信息
   */
  const user = ref(null)

  // --- 方法 ---

  /**
   * 登录
   * 流程：调用后端登录 API → 拿到 token 和用户信息 → 保存到 store 和 localStorage
   * @param {Object} data - 登录信息 { username, password }
   */
  async function login(data) {
    // 调用后端登录接口
    const res = await loginApi(data)
    // 保存 token 和用户信息到响应式状态
    token.value = res.data.access_token
    user.value = res.data.user
    // 持久化到 localStorage，刷新页面后可恢复
    localStorage.setItem('token', token.value)
    if (res.data.user) {
      localStorage.setItem('user', JSON.stringify(res.data.user))
    }
  }

  /**
   * 注册
   * 只调用后端注册接口，不保存任何状态
   * 注册后用户需要手动登录，这是常见的安全设计
   * @param {Object} data - 注册信息 { username, password }
   */
  async function register(data) {
    await registerApi(data)
  }

  /**
   * 获取当前用户信息
   * 使用已保存的 token 向后端请求用户详情
   * 通常在应用初始化时调用（如 App.vue 的 onMounted 中）
   */
  async function fetchUser() {
    // 如果没有 token，说明用户未登录，直接返回
    if (!token.value) return
    // 调用获取用户信息接口（token 由请求拦截器自动携带）
    const res = await getMe()
    user.value = res.data
    localStorage.setItem('user', JSON.stringify(res.data))
  }

  /**
   * 登出
   * 清除所有认证状态：token、用户信息、localStorage
   */
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 返回所有需要暴露的状态和方法
  // 只有返回的内容才能在组件中通过 store 实例访问
  return { token, user, login, register, fetchUser, logout }
})
