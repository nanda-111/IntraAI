/**
 * 知识库相关 API 模块
 *
 * 封装知识库 CRUD 操作的所有 HTTP 请求。
 * 统一从 api/index.js 获取配置好的 Axios 实例，自动携带 token 认证。
 */
import api from './index'

/**
 * 获取知识库列表
 * @param {string} [q] - 可选搜索关键词，按名称模糊匹配
 * @returns {Promise} Axios 请求 Promise，返回当前用户的知识库列表
 */
export function listKnowledgeBases(q) {
  return api.get('/api/knowledge-bases/', { params: q ? { q } : {} })
}

/**
 * 获取单个知识库详情
 * @param {string|number} id - 知识库 ID
 * @returns {Promise} Axios 请求 Promise，返回知识库对象
 */
export function getKnowledgeBase(id) {
  return api.get(`/api/knowledge-bases/${id}`)
}

/**
 * 创建知识库
 * @param {Object} data - 知识库信息 { name, description }
 * @returns {Promise} Axios 请求 Promise，返回新创建的知识库对象
 */
export function createKnowledgeBase(data) {
  return api.post('/api/knowledge-bases/', data)
}

/**
 * 更新知识库
 * @param {string|number} id - 知识库 ID
 * @param {Object} data - 要更新的字段 { name?, description? }
 * @returns {Promise} Axios 请求 Promise，返回更新后的知识库对象
 */
export function updateKnowledgeBase(id, data) {
  return api.put(`/api/knowledge-bases/${id}`, data)
}

/**
 * 删除知识库
 * @param {string|number} id - 要删除的知识库 ID
 * @returns {Promise} Axios 请求 Promise
 */
export function deleteKnowledgeBase(id) {
  return api.delete(`/api/knowledge-bases/${id}`)
}

/**
 * 清理数据库中已不存在对应文件夹的知识库（仅管理员）
 * @returns {Promise} Axios 请求 Promise，返回清理结果 { removed, count }
 */
export function cleanupOrphanKnowledgeBases() {
  return api.post('/api/knowledge-bases/cleanup')
}
