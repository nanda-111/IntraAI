/**
 * 对话 API 模块
 *
 * 封装与 AI 对话相关的后端接口请求。
 * 使用统一的 axios 实例（api），自动携带认证 token。
 */
import api from './index'

/**
 * 发送对话请求
 *
 * @param {Object} data - 请求数据
 * @param {string} data.question - 用户提出的问题
 * @param {number|null} data.kb_id - 可选的知识库 ID
 * @param {number|null} data.session_id - 可选的会话 ID，用于多轮对话上下文
 * @returns {Promise} 返回包含 AI 回答的响应对象
 */
export function sendChat(data) {
  return api.post('/api/chat/', data)
}
