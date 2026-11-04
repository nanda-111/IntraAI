import api from './index'

export const getBrands = () => api.get('/api/products/brands')
export const getModels = (params) => api.get('/api/products/models', { params })
export const getModel = (modelId) => api.get(`/api/products/models/${modelId}`)
export const getModelCapabilities = (modelId) =>
  api.get(`/api/products/models/${modelId}/capabilities`)
export const getModelErrorCodes = (modelId) =>
  api.get(`/api/products/models/${modelId}/error-codes`)
export const getFaultCategories = () => api.get('/api/products/fault-categories')

export const getDevices = () => api.get('/api/products/devices')
export const addDevice = (data) => api.post('/api/products/devices', data)
export const removeDevice = (modelId) => api.delete(`/api/products/devices/${modelId}`)
export const setCurrentDevice = (modelId) =>
  api.post(`/api/products/devices/${modelId}/current`)

// 管理端
export const adminListBrands = () => api.get('/api/admin/products/brands')
export const adminCreateBrand = (data) => api.post('/api/admin/products/brands', data)
export const adminUpdateBrand = (id, data) => api.put(`/api/admin/products/brands/${id}`, data)
export const adminCreateModel = (data) => api.post('/api/admin/products/models', data)
export const adminUpdateModel = (modelId, data) =>
  api.put(`/api/admin/products/models/${modelId}`, data)
export const adminDeleteModel = (modelId) => api.delete(`/api/admin/products/models/${modelId}`)
export const adminAddCapability = (modelId, data) =>
  api.post(`/api/admin/products/models/${modelId}/capabilities`, data)
export const adminUpdateCapability = (id, data) =>
  api.put(`/api/admin/products/capabilities/${id}`, data)
export const adminDeleteCapability = (id) =>
  api.delete(`/api/admin/products/capabilities/${id}`)