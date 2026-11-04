import { createRouter, createWebHistory } from 'vue-router'
import PlatformLayout from '../components/PlatformLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    component: PlatformLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/user/DashboardView.vue'),
        meta: { requiresAuth: true, title: '服务首页' },
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('../views/user/ProductCatalogView.vue'),
        meta: { requiresAuth: true, title: '品牌与型号中心' },
      },
      {
        path: 'products/:id',
        name: 'ProductDetail',
        component: () => import('../views/user/ProductDetailView.vue'),
        meta: { requiresAuth: true, title: '型号详情' },
      },
      {
        path: 'knowledge',
        name: 'KnowledgeCenter',
        component: () => import('../views/user/KnowledgeCenterView.vue'),
        meta: { requiresAuth: true, title: '知识中心' },
      },
      {
        path: 'assistant',
        name: 'Assistant',
        component: () => import('../views/user/AssistantView.vue'),
        meta: { requiresAuth: true, title: '智能客服' },
      },
      {
        path: 'diagnosis',
        name: 'Diagnosis',
        component: () => import('../views/user/DiagnosisWorkspaceView.vue'),
        meta: { requiresAuth: true, title: '故障诊断' },
      },
      {
        path: 'diagnosis/:id',
        name: 'DiagnosisDetail',
        component: () => import('../views/user/DiagnosisDetailView.vue'),
        meta: { requiresAuth: true, title: '诊断详情' },
      },
      {
        path: 'tickets',
        name: 'Tickets',
        component: () => import('../views/user/TicketListView.vue'),
        meta: { requiresAuth: true, title: '售后工单' },
      },
      {
        path: 'tickets/:id',
        name: 'TicketDetail',
        component: () => import('../views/user/TicketDetailView.vue'),
        meta: { requiresAuth: true, title: '工单详情' },
      },
      {
        path: 'maintenance',
        name: 'Maintenance',
        component: () => import('../views/user/MaintenanceView.vue'),
        meta: { requiresAuth: true, title: '维护与耗材指南' },
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('../views/user/HistoryView.vue'),
        meta: { requiresAuth: true, title: '我的服务记录' },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/user/ProfileView.vue'),
        meta: { requiresAuth: true, title: '个人中心' },
      },
      {
        path: 'admin/dashboard',
        name: 'AdminDashboard',
        component: () => import('../views/admin/AdminDashboardView.vue'),
        meta: { requiresAuth: true, requiresStaff: true, title: '运营概览' },
      },
      {
        path: 'admin/products',
        name: 'AdminProducts',
        component: () => import('../views/admin/ModelAdminView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '品牌型号管理' },
      },
      {
        path: 'admin/knowledge/sources',
        name: 'AdminSources',
        component: () => import('../views/admin/KnowledgeSourcesView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '知识来源管理' },
      },
      {
        path: 'admin/knowledge/import',
        name: 'AdminImport',
        component: () => import('../views/admin/KnowledgeImportView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '文档导入' },
      },
      {
        path: 'admin/knowledge/review',
        name: 'AdminReview',
        component: () => import('../views/admin/KnowledgeReviewView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '知识审核发布' },
      },
      {
        path: 'admin/cases',
        name: 'AdminCases',
        component: () => import('../views/admin/RepairCaseAdminView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '维修案例管理' },
      },
      {
        path: 'admin/tickets',
        name: 'AdminTickets',
        component: () => import('../views/admin/TicketAdminView.vue'),
        meta: { requiresAuth: true, roles: ['agent', 'system_admin'], title: '售后工单管理' },
      },
      {
        path: 'admin/evaluation',
        name: 'AdminEvaluation',
        component: () => import('../views/admin/EvaluationView.vue'),
        meta: { requiresAuth: true, roles: ['knowledge_admin', 'system_admin'], title: '评测中心' },
      },
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('../views/admin/UserAdminView.vue'),
        meta: { requiresAuth: true, roles: ['system_admin'], title: '用户与权限' },
      },
      {
        path: 'admin/settings',
        name: 'AdminSettings',
        component: () => import('../views/admin/SettingsView.vue'),
        meta: { requiresAuth: true, roles: ['system_admin'], title: '系统配置与日志' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function currentRole() {
  try {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (!user) return 'user'
    if (user.role && user.role !== 'user') return user.role
    return user.is_admin ? 'system_admin' : 'user'
  } catch {
    return 'user'
  }
}

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  if (requiresAuth && !token) return '/login'
  if (token && to.path === '/login') return '/dashboard'

  const role = currentRole()
  const requiresStaff = to.matched.some((record) => record.meta.requiresStaff)
  if (requiresStaff && role === 'user') return '/dashboard'

  const roleRule = [...to.matched].reverse().find((record) => record.meta.roles)
  if (roleRule && !roleRule.meta.roles.includes(role)) return '/dashboard'
  return true
})

export default router