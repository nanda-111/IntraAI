import api from './index'

export const listKnowledge = (params) => api.get('/api/knowledge', { params })
export const getKnowledge = (docId) => api.get(`/api/knowledge/${docId}`)

// 管理端知识运营
export const listSources = () => api.get('/api/admin/knowledge/sources')
export const createSource = (data) => api.post('/api/admin/knowledge/sources', data)
export const updateSource = (id, data) => api.put(`/api/admin/knowledge/sources/${id}`, data)
export const deleteSource = (id) => api.delete(`/api/admin/knowledge/sources/${id}`)

export const importDocument = (formData) =>
  api.post('/api/admin/knowledge/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
export const listDocuments = (params) => api.get('/api/admin/knowledge/documents', { params })

export const adminListKnowledge = (params) => api.get('/api/admin/knowledge', { params })
export const adminGetKnowledge = (docId) => api.get(`/api/admin/knowledge/${docId}`)
export const adminCreateKnowledge = (data) => api.post('/api/admin/knowledge', data)
export const adminUpdateKnowledge = (docId, data) =>
  api.put(`/api/admin/knowledge/${docId}`, data)
export const adminDeleteKnowledge = (docId) => api.delete(`/api/admin/knowledge/${docId}`)
export const reviewKnowledge = (docId, data) =>
  api.post(`/api/admin/knowledge/${docId}/review`, data)
export const reindexKnowledge = () => api.post('/api/admin/knowledge/reindex')
export const getIndexStatus = () => api.get('/api/admin/knowledge/index-status')
export const getKnowledgeMeta = () => api.get('/api/admin/knowledge/meta/categories')