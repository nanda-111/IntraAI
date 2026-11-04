import api from './index'

export const listDatasets = () => api.get('/api/admin/evaluation/datasets')
export const createDataset = (data) => api.post('/api/admin/evaluation/datasets', data)
export const updateDataset = (id, data) => api.put(`/api/admin/evaluation/datasets/${id}`, data)
export const deleteDataset = (id) => api.delete(`/api/admin/evaluation/datasets/${id}`)
export const listItems = (datasetId) =>
  api.get(`/api/admin/evaluation/datasets/${datasetId}/items`)
export const createItem = (datasetId, data) =>
  api.post(`/api/admin/evaluation/datasets/${datasetId}/items`, data)
export const deleteItem = (datasetId, itemId) =>
  api.delete(`/api/admin/evaluation/datasets/${datasetId}/items/${itemId}`)
export const runEvaluation = (datasetId) =>
  api.post(`/api/admin/evaluation/datasets/${datasetId}/run`)
export const listRuns = (params) => api.get('/api/admin/evaluation/runs', { params })
export const getRun = (id) => api.get(`/api/admin/evaluation/runs/${id}`)