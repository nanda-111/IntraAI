import api from './index'

export const getDashboard = (params) => api.get('/api/admin/dashboard', { params })
export const getSettings = () => api.get('/api/admin/settings')
export const getAuditLogs = (params) => api.get('/api/admin/audit-logs', { params })
export const getRetrievalLogs = (params) => api.get('/api/admin/retrieval-logs', { params })
export const getUsers = () => api.get('/api/admin/users')
export const setUserRole = (id, role) => api.put(`/api/admin/users/${id}/role`, { role })
export const toggleUserActive = (id) => api.put(`/api/admin/users/${id}/toggle`)
export const getFaultCategories = () => api.get('/api/admin/fault-categories')

// 维修案例
export const listCases = (params) => api.get('/api/admin/cases', { params })
export const createCase = (data) => api.post('/api/admin/cases', data)
export const updateCase = (caseId, data) => api.put(`/api/admin/cases/${caseId}`, data)
export const deleteCase = (caseId) => api.delete(`/api/admin/cases/${caseId}`)
export const importCases = (formData) =>
  api.post('/api/admin/cases/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })