<!--
  管理后台页面
  实现四个功能 Tab：数据概览、用户管理、知识库管理、操作日志
  采用经典的「顶部导航 + 左侧菜单 + 右侧内容」三段式布局
-->
<template>
  <div class="app-layout">
    <!-- 深色侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-top">
        <div class="sidebar-logo">
          IntraAI
        </div>
      </div>
      <div class="sidebar-bottom">
        <div class="nav-links">
          <router-link
            to="/"
            class="nav-link"
          >
            对话
          </router-link>
          <router-link
            to="/knowledge"
            class="nav-link"
          >
            知识库
          </router-link>
          <router-link
            to="/admin"
            class="nav-link active"
          >
            管理
          </router-link>
        </div>
        <button
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </aside>

    <main class="main-content-admin">
      <a-layout>
        <!--
        a-layout-sider：左侧菜单栏
        使用 light 主题，宽度固定 200px
        v-model:selected-keys 双向绑定当前选中的 Tab
        用户点击菜单项时，activeTab 自动更新，触发 watch 加载对应数据
      -->
        <a-layout-sider
          width="200"
          theme="light"
        >
          <a-menu
            v-model:selected-keys="activeTab"
            mode="inline"
            style="height: 100%"
          >
            <a-menu-item key="stats">
              数据概览
            </a-menu-item>
            <a-menu-item key="users">
              用户管理
            </a-menu-item>
            <a-menu-item key="kbs">
              知识库管理
            </a-menu-item>
            <a-menu-item key="logs">
              操作日志
            </a-menu-item>
          </a-menu>
        </a-layout-sider>

        <!-- 右侧内容区：根据 activeTab 的值显示对应的面板 -->
        <a-layout-content style="padding: 24px">
          <!-- ==================== 数据概览面板 ==================== -->
          <template v-if="activeTab[0] === 'stats'">
            <!-- 四列卡片，每列展示一项统计数据 -->
            <a-row :gutter="16">
              <a-col
                v-for="item in statCards"
                :key="item.title"
                :span="6"
              >
                <a-card>
                  <!-- a-statistic：Ant Design Vue 的数值展示组件 -->
                  <a-statistic
                    :title="item.title"
                    :value="item.value"
                  />
                </a-card>
              </a-col>
            </a-row>
          </template>

          <!-- ==================== 用户管理面板 ==================== -->
          <template v-if="activeTab[0] === 'users'">
            <a-card title="用户管理">
              <!--
              a-table 用户列表表格
              :loading 绑定加载状态，请求期间显示加载动画
              row-key="id" 指定每行的唯一标识字段
            -->
              <a-table
                :data-source="users"
                :columns="userColumns"
                row-key="id"
                :loading="loadingUsers"
              >
                <template #bodyCell="{ column, record }">
                  <!-- 状态列：使用 a-tag 显示用户是否活跃 -->
                  <template v-if="column.key === 'status'">
                    <!--
                    a-tag 状态标签
                    通过 :color 动态绑定颜色：
                    - 活跃用户显示绿色（green）
                    - 禁用用户显示红色（red）
                  -->
                    <a-tag :color="record.is_active ? 'green' : 'red'">
                      {{ record.is_active ? '正常' : '禁用' }}
                    </a-tag>
                  </template>
                  <!-- 角色列：区分管理员和普通用户 -->
                  <template v-if="column.key === 'admin'">
                    <!-- 管理员标签为蓝色，普通用户为默认灰色 -->
                    <a-tag :color="record.is_admin ? 'blue' : 'default'">
                      {{ record.is_admin ? '管理员' : '用户' }}
                    </a-tag>
                  </template>
                  <!-- 操作列：提供启用/禁用和设置管理员两个操作按钮 -->
                  <template v-if="column.key === 'action'">
                    <a-space>
                      <a-button
                        size="small"
                        @click="handleToggleUser(record)"
                      >
                        {{ record.is_active ? '禁用' : '启用' }}
                      </a-button>
                      <a-button
                        size="small"
                        @click="handleToggleAdmin(record)"
                      >
                        {{ record.is_admin ? '取消管理员' : '设为管理员' }}
                      </a-button>
                    </a-space>
                  </template>
                </template>
              </a-table>
            </a-card>
          </template>

          <!-- ==================== 知识库管理面板 ==================== -->
          <template v-if="activeTab[0] === 'kbs'">
            <a-card title="知识库管理">
              <!-- 知识库列表，展示所有用户的全部知识库 -->
              <a-table
                :data-source="adminKbs"
                :columns="kbColumns"
                row-key="id"
                :loading="loadingKbs"
              />
            </a-card>
          </template>

          <!-- ==================== 操作日志面板 ==================== -->
          <template v-if="activeTab[0] === 'logs'">
            <a-card title="操作日志">
              <!--
              a-table 操作日志表格
              配置分页组件：
              - current: 当前页码，双向绑定 logPage
              - total: 总记录数，由后端返回
              - pageSize: 每页显示 20 条
              - onChange: 用户切换页码时触发 handleLogPageChange，加载对应页的数据
            -->
              <a-table
                :data-source="logs"
                :columns="logColumns"
                row-key="id"
                :loading="loadingLogs"
                :pagination="{ current: logPage, total: logTotal, pageSize: 20, onChange: handleLogPageChange }"
              />
            </a-card>
          </template>
        </a-layout-content>
      </a-layout>
    </main>
  </div>
</template>

<script setup>
/**
 * 管理后台页面脚本
 *
 * 核心逻辑：
 * - activeTab 维护当前选中的左侧菜单项
 * - watch 监听 activeTab 变化，切换 Tab 时自动加载对应数据
 * - 每个 Tab 的数据独立获取，互不干扰
 * - computed 派生统计数据卡片数组，statCards 自动响应 stats.value 的变化
 */
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import {
  getStats,
  getUsers,
  toggleUser,
  toggleAdmin,
  getAdminKnowledgeBases,
  getUsageLogs
} from '../api/admin'

// 路由实例，用于页面跳转
const router = useRouter()
// 认证状态管理，用于退出登录和获取用户信息
const authStore = useAuthStore()

// ==================== 当前选中的 Tab ====================
// 使用数组形式是因为 Ant Design 的 Menu 组件 v-model:selected-keys 接受数组
// 默认选中「数据概览」Tab
const activeTab = ref(['stats'])

// ==================== 数据概览 ====================
// 平台统计数据对象，包含 user_count、active_user_count、kb_count、chat_count 等字段
const stats = ref({})

/**
 * computed 派生统计数据卡片数组
 *
 * 使用 computed 的好处：
 * 1. 当 stats.value 变化时，statCards 自动重新计算，无需手动同步
 * 2. 模板中直接使用 statCards 即可获取最新数据
 * 3. 依赖追踪由 Vue 自动管理，无需手动清理
 */
const statCards = computed(() => [
  { title: '总用户数', value: stats.value.user_count || 0 },
  { title: '活跃用户', value: stats.value.active_user_count || 0 },
  { title: '知识库数', value: stats.value.kb_count || 0 },
  { title: '对话次数', value: stats.value.chat_count || 0 },
])

// ==================== 用户管理 ====================
// 用户列表数据
const users = ref([])
// 用户列表加载状态
const loadingUsers = ref(false)
// 用户表格列定义：key 用于 bodyCell 插槽中的条件渲染
const userColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户名', dataIndex: 'username' },
  { title: '邮箱', dataIndex: 'email' },
  { title: '状态', key: 'status' },
  { title: '角色', key: 'admin' },
  { title: '注册时间', dataIndex: 'created_at' },
  { title: '操作', key: 'action', width: 250 },
]

// ==================== 知识库管理 ====================
// 管理员视角的知识库列表
const adminKbs = ref([])
// 知识库加载状态
const loadingKbs = ref(false)
// 知识库表格列定义
const kbColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '名称', dataIndex: 'name' },
  { title: '描述', dataIndex: 'description' },
  { title: '所有者', dataIndex: 'owner' },
  { title: '文档数', dataIndex: 'doc_count' },
  { title: '创建时间', dataIndex: 'created_at' },
]

// ==================== 操作日志 ====================
// 日志列表数据
const logs = ref([])
// 日志总记录数，用于分页组件
const logTotal = ref(0)
// 日志当前页码
const logPage = ref(1)
// 日志加载状态
const loadingLogs = ref(false)
// 日志表格列定义
const logColumns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '用户', dataIndex: 'user' },
  { title: '操作', dataIndex: 'action' },
  { title: '时间', dataIndex: 'created_at' },
]

// ==================== 数据获取函数 ====================

/**
 * 获取平台统计数据
 * 调用 GET /api/admin/stats，更新 stats 响应式对象
 * 页面加载时自动调用（onMounted），切换到数据概览 Tab 时也会通过 watch 调用
 */
async function fetchStats() {
  const res = await getStats()
  stats.value = res.data
}

/**
 * 获取用户列表
 * 使用 try/finally 确保加载状态在请求完成后正确重置
 */
async function fetchUsers() {
  loadingUsers.value = true
  try {
    const res = await getUsers()
    users.value = res.data
  } finally {
    loadingUsers.value = false
  }
}

/**
 * 获取管理后台视角的知识库列表
 * 返回所有用户的全部知识库
 */
async function fetchKbs() {
  loadingKbs.value = true
  try {
    const res = await getAdminKnowledgeBases()
    adminKbs.value = res.data
  } finally {
    loadingKbs.value = false
  }
}

/**
 * 获取操作日志（分页）
 * @param {number} page - 页码，默认为 1
 * 后端返回 { items: [], total: number } 格式的数据
 */
async function fetchLogs(page = 1) {
  loadingLogs.value = true
  try {
    const res = await getUsageLogs({ page, size: 20 })
    logs.value = res.data.items
    logTotal.value = res.data.total
    logPage.value = page
  } finally {
    loadingLogs.value = false
  }
}

// ==================== 操作函数 ====================

/**
 * 切换用户启用/禁用状态
 * 操作成功后自动刷新用户列表
 */
async function handleToggleUser(record) {
  await toggleUser(record.id)
  message.success('操作成功')
  fetchUsers()
}

/**
 * 切换用户管理员权限
 * 操作成功后自动刷新用户列表
 */
async function handleToggleAdmin(record) {
  await toggleAdmin(record.id)
  message.success('操作成功')
  fetchUsers()
}

/**
 * 日志分页切换回调
 * @param {number} page - 用户点击的目标页码
 * 由 a-table 的 pagination.onChange 触发
 */
function handleLogPageChange(page) {
  fetchLogs(page)
}

/**
 * 退出登录
 * 清除本地认证状态并跳转到登录页面
 */
function handleLogout() {
  authStore.logout()
  router.push('/login')
}

// ==================== Tab 切换数据加载 ====================
/**
 * watch 监听 activeTab 变化
 *
 * 工作原理：
 * - activeTab 是一个 ref 数组，当用户点击侧边栏菜单项时，v-model 自动更新它的值
 * - watch 捕获变化，取出数组第一个元素（当前选中的 Tab key）
 * - 根据 Tab key 调用对应的数据获取函数
 *
 * 注意：切换到某个 Tab 时会触发数据加载，确保每次切换都能看到最新数据
 * 而且每个 Tab 的数据是独立获取的，不会因为加载一个 Tab 的数据而影响其他 Tab
 */
watch(activeTab, ([tab]) => {
  if (tab === 'stats') fetchStats()
  if (tab === 'users') fetchUsers()
  if (tab === 'kbs') fetchKbs()
  if (tab === 'logs') fetchLogs()
})

/**
 * 页面挂载时的初始化操作
 * 1. 获取当前登录用户信息（用于权限控制和导航显示）
 * 2. 加载默认 Tab（数据概览）的数据
 */
onMounted(() => {
  authStore.fetchUser()
  fetchStats()
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 260px;
  background: #1a1a2e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-top {
  flex: 1;
  padding: 16px;
}

.sidebar-logo {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  padding: 4px 0;
}

.sidebar-bottom {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.nav-link {
  color: #aaa;
  text-decoration: none;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.nav-link:hover,
.nav-link.active {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.logout-btn {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #aaa;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.logout-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

.main-content-admin {
  flex: 1;
  display: flex;
  background: #f7f7f8;
  overflow: hidden;
}
</style>
