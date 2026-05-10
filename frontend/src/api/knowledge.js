/**
 * 知识库相关 API 模块
 *
 * 封装知识库 CRUD 操作的所有 HTTP 请求。
 * 统一从 api/index.js 获取配置好的 Axios 实例，自动携带 token 认证。
 *
 * 关于 API 封装的设计思想，请参见 api/auth.js 中的注释。
 */
import api from './index'

/**
 * 获取知识库列表
 * @returns {Promise} Axios 请求 Promise，返回当前用户的知识库列表
 */
export function listKnowledgeBases() {
  return api.get('/api/knowledge-bases/')
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
 * 删除知识库
 * @param {string|number} id - 要删除的知识库 ID
 * @returns {Promise} Axios 请求 Promise
 */
export function deleteKnowledgeBase(id) {
  return api.delete(`/api/knowledge-bases/${id}`)
}
