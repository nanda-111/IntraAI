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

/**
 * 发送流式对话请求（SSE）
 *
 * 使用 fetch + ReadableStream 处理 Server-Sent Events。
 * 返回 AsyncGenerator，调用方用 for await...of 消费。
 *
 * 每次 yield 一个对象：
 *   { type: "reasoning", content: "..." }  — 思考过程片段
 *   { type: "answer", content: "..." }     — 回答片段
 *
 * @param {Object} data - 请求数据 { question, kb_id, session_id, mode }
 * @returns {AsyncGenerator} 流式数据生成器
 */
export async function* sendChatStream(data) {
  const token = localStorage.getItem('token')
  const baseURL = import.meta.env.PROD ? '' : 'http://localhost:8000'
  const res = await fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw new Error(`Stream request failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') return
        if (raw === '[ERROR]') throw new Error('Stream error')
        try {
          yield JSON.parse(raw)
        } catch {
          yield { type: 'answer', content: raw }
        }
      }
    }
  }
}
