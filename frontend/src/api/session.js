/**
 * 会话 API 模块
 *
 * 封装会话管理相关的后端接口请求。
 */
import api from './index'

/**
 * 创建新会话
 * @returns {Promise} 返回新创建的会话对象
 */
export function createSession() {
  return api.post('/api/sessions/')
}

/**
 * 获取当前用户所有会话
 * @returns {Promise} 返回会话列表（按更新时间倒序）
 */
export function listSessions() {
  return api.get('/api/sessions/')
}

/**
 * 获取会话详情（含对话记录）
 * @param {number} id - 会话 ID
 * @returns {Promise} 返回会话详情对象
 */
export function getSession(id) {
  return api.get(`/api/sessions/${id}`)
}

/**
 * 删除会话及其下所有对话记录
 * @param {number} id - 要删除的会话 ID
 * @returns {Promise}
 */
export function deleteSession(id) {
  return api.delete(`/api/sessions/${id}`)
}
