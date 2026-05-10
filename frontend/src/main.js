/**
 * 前端应用入口文件
 *
 * 该文件负责：
 * 1. 创建 Vue 应用实例
 * 2. 注册所需的插件（Pinia、Vue Router、Ant Design Vue）
 * 3. 将应用挂载到 DOM 中的 #app 元素上
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
// 引入 Ant Design Vue 的重置样式，统一各浏览器的默认样式
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
// 引入路由配置
import router from './router'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Pinia — 状态管理库
// Pinia 用于在组件之间共享数据（如用户登录状态、全局配置等）
// 类似于 Vuex，但 API 更简洁，对 TypeScript 支持更好
app.use(createPinia())

// 注册 Vue Router — 路由库
// 管理页面跳转，根据 URL 渲染不同的页面组件
app.use(router)

// 注册 Ant Design Vue — UI 组件库
// 全局注册所有 Ant Design Vue 组件，无需逐个 import
app.use(Antd)

// 将 Vue 应用挂载到页面中的 #app 元素
app.mount('#app')
