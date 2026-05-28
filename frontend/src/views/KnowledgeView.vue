<!--
  知识库管理页面
  - 顶部导航栏：提供对话、知识库、管理页面的切换入口
  - 主内容区：知识库列表表格 + 新建/删除功能
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
            class="nav-link active"
          >
            知识库
          </router-link>
          <router-link
            v-if="authStore.user?.is_admin"
            to="/admin"
            class="nav-link"
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

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <a-card title="知识库管理">
          <!--
          #extra 插槽：卡片右上角的额外操作区域
          放置"新建知识库"按钮，点击后打开弹窗
        -->
          <template #extra>
            <a-button
              type="primary"
              @click="showCreate = true"
            >
              新建知识库
            </a-button>
          </template>

          <!--
          a-table 知识库列表表格：
          - data-source：表格数据源，绑定 kbs 响应式数组
          - columns：列配置数组，定义每列的标题、数据字段、key 等
          - loading：加载状态，为 true 时显示加载动画
          - row-key：每行数据的唯一标识字段，此处使用 "id"

          columns 配置说明：
          - dataIndex：对应数据对象中的字段名，用于从行数据中取值显示
          - key：列的唯一标识，用于 #bodyCell 插槽中判断当前渲染的是哪一列
            （dataIndex 和 key 可以相同，但 key 仅用于标识列，不用于取值；
             当列不需要直接显示数据（如操作列）时，只设置 key 即可）
          - title：列头显示的文字
          - width：列的固定宽度（像素）

          #bodyCell 插槽：
          自定义表格单元格的渲染内容。插槽参数：
          - column：当前列的配置对象
          - record：当前行的数据对象
          通过判断 column.key === 'action' 来为"操作"列渲染删除按钮。
        -->
          <a-table
            :data-source="kbs"
            :columns="columns"
            :loading="loading"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'action'">
                <!--
                a-popconfirm 气泡确认框：
                - title：确认提示文字
                - @confirm：用户点击"确定"后触发的回调
                用户点击"删除"按钮后，会弹出气泡确认框；
                点击"确认"才执行 handleDelete，点击"取消"则不做任何操作。
                这是一种防止误删的交互保护。
              -->
                <a-popconfirm
                  title="确认删除？"
                  @confirm="handleDelete(record.id)"
                >
                  <a-button
                    type="link"
                    danger
                  >
                    删除
                  </a-button>
                </a-popconfirm>
              </template>
            </template>
          </a-table>
        </a-card>

        <!--
        a-modal 新建知识库弹窗：
        - v-model:open：双向绑定弹窗的显示/隐藏状态
          这是 Vue 3 的 v-model 语法糖：
          - 父组件通过 showCreate 控制弹窗是否可见
          - 弹窗内部关闭时（点 X、点遮罩、按 Esc）会自动将 open 更新为 false
          - @ok 点击确定按钮时触发 handleCreate
        - title：弹窗标题
        - @ok：点击确定按钮的回调
      -->
        <a-modal
          v-model:open="showCreate"
          title="新建知识库"
          @ok="handleCreate"
        >
          <!-- a-form 表单，layout="vertical" 使用垂直布局（标签在上，输入框在下） -->
          <a-form layout="vertical">
            <!--
            a-form-item 表单项：
            - label：标签文字
            - required：是否必填（显示红色星号标记）
          -->
            <a-form-item
              label="名称"
              required
            >
              <!-- a-input 文本输入框，v-model:value 双向绑定 newKb.name -->
              <a-input v-model:value="newKb.name" />
            </a-form-item>
            <a-form-item label="描述">
              <!-- a-textarea 多行文本输入框，用于输入知识库描述 -->
              <a-textarea v-model:value="newKb.description" />
            </a-form-item>
          </a-form>
        </a-modal>
      </div>
    </main>
  </div>
</template>

<script setup>
/**
 * 知识库管理页面脚本
 *
 * 功能：
 * - 获取并展示知识库列表
 * - 新建知识库
 * - 删除知识库
 * - 退出登录
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'
import { listKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase } from '../api/knowledge'

// 路由实例，用于页面跳转
const router = useRouter()

// 认证状态仓库，存储当前用户信息和登录状态
const authStore = useAuthStore()

// 知识库列表数据（响应式数组，数据变化时表格自动更新）
const kbs = ref([])

// 表格加载状态（为 true 时显示加载动画）
const loading = ref(false)

// 新建弹窗的显示状态（true = 显示，false = 隐藏）
const showCreate = ref(false)

// 新建知识库的表单数据（reactive 创建响应式对象）
// 使用 reactive 而非 ref，是因为对象内部属性的修改会自动触发响应式更新
const newKb = reactive({ name: '', description: '' })

/**
 * 表格列配置数组
 *
 * 每个列对象的属性：
 * - title：列头显示的文字
 * - dataIndex：从行数据中取值的字段名（对应数据对象的属性名）
 * - key：列的唯一标识符（用于 #bodyCell 插槽中判断当前列）
 * - width：列宽（像素）
 *
 * 注意：操作列没有 dataIndex，因为它不显示数据，
 * 而是通过 #bodyCell 插槽自定义渲染内容。
 */
const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 100 },
]

/**
 * 获取知识库列表
 * 调用 API 获取所有知识库数据，赋值给 kbs 响应式变量
 */
async function fetchKbs() {
  loading.value = true
  try {
    const res = await listKnowledgeBases()
    kbs.value = res.data
  } finally {
    // 无论成功或失败，都关闭加载状态
    loading.value = false
  }
}

/**
 * 创建知识库
 * 提交表单数据到后端，成功后关闭弹窗、重置表单、刷新列表
 */
async function handleCreate() {
  await createKnowledgeBase(newKb)
  message.success('创建成功')
  // 关闭弹窗
  showCreate.value = false
  // 重置表单数据，为下次新建做准备
  newKb.name = ''
  newKb.description = ''
  // 重新获取列表，展示新创建的知识库
  fetchKbs()
}

/**
 * 删除知识库
 * @param {number} id - 要删除的知识库 ID
 * 删除成功后刷新列表
 */
async function handleDelete(id) {
  await deleteKnowledgeBase(id)
  message.success('已删除')
  fetchKbs()
}

/**
 * 退出登录
 * 清除认证状态并跳转到登录页
 */
function handleLogout() {
  authStore.logout()
  router.push('/login')
}

/**
 * onMounted 生命周期钩子：
 *
 * 在 Vue 组件挂载到 DOM 之后执行。
 * "挂载"指的是组件的模板已被编译并插入到页面 DOM 树中，
 * 此时可以安全地操作 DOM 或发起异步请求。
 *
 * 这里在 onMounted 中：
 * 1. 先获取当前登录用户信息（需要 token 验证）
 * 2. 再获取知识库列表
 *
 * 两个请求按顺序执行（await），确保用户信息就绪后再加载数据。
 */
onMounted(async () => {
  await authStore.fetchUser()
  fetchKbs()
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

.main-content {
  flex: 1;
  background: #f7f7f8;
  overflow-y: auto;
  padding: 24px;
}

.content-container {
  max-width: 960px;
  margin: 0 auto;
}
</style>
