/**
 * 路由配置文件
 *
 * 核心概念：
 * - 路由：定义 URL 路径和页面组件之间的映射关系
 * - 懒加载（lazy loading）：使用 () => import(...) 语法，只有当用户访问该页面时
 *   才会下载对应的 JS 文件，减少首屏加载时间
 * - meta 字段：给路由附加自定义信息（如 requiresAuth），供路由守卫判断使用
 * - createWebHistory vs createWebHashHistory：
 *   - createWebHistory：URL 格式为 /login（更美观，需要服务器配置回退路由）
 *   - createWebHashHistory：URL 格式为 /#/login（带 # 号，兼容性更好，无需服务器配置）
 */
import { createRouter, createWebHistory } from 'vue-router'

// 路由配置 — 定义 URL 路径和页面组件的映射关系
const routes = [
  {
    path: '/login',
    name: 'Login',
    // 懒加载：只在用户访问 /login 时才下载 LoginView.vue 对应的 JS 文件
    // 好处：减少首屏加载体积，提升初始加载速度
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('../views/ChatView.vue'),
    // meta.requiresAuth = true 表示该页面需要登录才能访问
    // 路由守卫会读取此字段进行权限判断
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../views/KnowledgeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/AdminView.vue'),
    // 同时要求登录和管理员权限
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

// 创建路由实例
const router = createRouter({
  // 使用 HTML5 History 模式（URL 不带 # 号）
  // 注意：生产环境需要服务器将所有路径回退到 index.html，否则刷新会 404
  history: createWebHistory(),
  routes,
})

/**
 * 全局前置守卫（beforeEach）
 *
 * 执行时机：在每次路由跳转之前自动执行
 * 执行顺序：to（目标路由）→ 守卫判断 → next（决定是否放行）
 *
 * 工作流程：
 * 1. 用户点击链接或调用 router.push()
 * 2. 触发 beforeEach 守卫
 * 3. 检查目标路由是否需要登录（to.meta.requiresAuth）
 * 4. 如果需要登录但没有 token，重定向到 /login
 * 5. 否则放行，继续加载目标页面
 */
router.beforeEach((to, from, next) => {
  // 从浏览器本地存储中获取登录令牌
  const token = localStorage.getItem('token')

  // 如果目标页面需要登录，但用户没有 token，则跳转到登录页
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    // 放行，继续路由跳转
    next()
  }
})

export default router
