import api from './index'

export const listTickets = (params) => api.get('/api/tickets', { params })
export const getTicket = (id) => api.get(`/api/tickets/${id}`)
export const createTicket = (data) => api.post('/api/tickets', data)
export const commentTicket = (id, content) => api.post(`/api/tickets/${id}/comments`, { content })
export const closeTicket = (id, note) => api.post(`/api/tickets/${id}/close`, { note })

// 管理端
export const adminListTickets = (params) => api.get('/api/admin/tickets', { params })
export const adminGetTicket = (id) => api.get(`/api/admin/tickets/${id}`)
export const adminUpdateTicket = (id, data) => api.put(`/api/admin/tickets/${id}`, data)
export const getAssignees = () => api.get('/api/admin/tickets/assignees')