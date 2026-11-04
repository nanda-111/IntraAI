import api from './index'

export const listSessions = () => api.get('/api/assistant/sessions')
export const createSession = (data) => api.post('/api/assistant/sessions', data)
export const getSession = (id) => api.get(`/api/assistant/sessions/${id}`)
export const deleteSession = (id) => api.delete(`/api/assistant/sessions/${id}`)
export const sendMessage = (id, content) =>
  api.post(`/api/assistant/sessions/${id}/messages`, { content })
export const getSuggestions = (modelId) =>
  api.get('/api/assistant/suggestions', { params: { model_id: modelId } })
export const submitFeedback = (data) => api.post('/api/assistant/feedback', data)

/**
 * SSE 流式消息：使用 fetch 读取 data: 行，逐条回调。
 * 返回 AbortController，可调用 abort() 取消。
 */
export function streamMessage(id, content, onEvent) {
  const controller = new AbortController()
  const token = localStorage.getItem('token') || ''
  const base = import.meta.env.PROD ? '' : 'http://localhost:8000'

  fetch(`${base}/api/assistant/sessions/${id}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        onEvent({ type: 'error', content: text || '请求失败' })
        return
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false
      while (!finished) {
        const { done, value } = await reader.read()
        if (done) {
          finished = true
          break
        }
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''
        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data:')) continue
          const payload = line.slice(5).trim()
          if (!payload) continue
          if (payload === '[DONE]') {
            onEvent({ type: 'done' })
            continue
          }
          try {
            onEvent(JSON.parse(payload))
          } catch {
            // 忽略无法解析的片段
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onEvent({ type: 'error', content: '网络异常，请稍后重试' })
      }
    })

  return controller
}