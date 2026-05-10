/**
 * 管理后台 API 模块
 *
 * 本模块封装了管理后台所需的全部 API 请求，供管理后台页面组件调用。
 * 所有请求均通过统一的 axios 实例（api）发出，自动携带认证 token。
 */
import api from './index'

/**
 * 获取平台统计数据
 * 返回平台总用户数、知识库数量等汇总信息。
 */
export function getStats() {
  return api.get('/api/admin/stats')
}

/**
 * 获取所有用户列表
 * 返回平台内所有注册用户的信息，供管理员查看和管理。
 */
export function getUsers() {
  return api.get('/api/admin/users')
}

/**
 * 启用/禁用用户
 * @param {number|string} id - 用户 ID
 * 切换目标用户的启用状态（冻结/解冻账号）。
 */
export function toggleUser(id) {
  return api.put(`/api/admin/users/${id}/toggle`)
}

/**
 * 设置/取消管理员
 * @param {number|string} id - 用户 ID
 * 切换目标用户的管理员权限（授予/撤销管理员角色）。
 */
export function toggleAdmin(id) {
  return api.put(`/api/admin/users/${id}/admin`)
}

/**
 * 获取所有知识库（管理视图）
 * 返回平台内所有知识库，用于管理后台的知识库管理页面。
 */
export function getAdminKnowledgeBases() {
  return api.get('/api/admin/knowledge-bases')
}

/**
 * 获取操作日志（分页）
 * @param {object} params - 查询参数，如 { page: 1, page_size: 20 }
 * 返回平台操作日志列表，支持分页查询。
 */
export function getUsageLogs(params) {
  return api.get('/api/admin/usage-logs', { params })
}
