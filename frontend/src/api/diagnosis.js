import api from './index'

export const createDiagnosis = (data) => api.post('/api/diagnosis/sessions', data)
export const listDiagnoses = (params) => api.get('/api/diagnosis/sessions', { params })
export const getDiagnosis = (id) => api.get(`/api/diagnosis/sessions/${id}`)
export const sendDiagnosisMessage = (id, content) =>
  api.post(`/api/diagnosis/sessions/${id}/messages`, { content })
export const submitStepResult = (id, stepId, data) =>
  api.post(`/api/diagnosis/sessions/${id}/steps/${stepId}/result`, data)
export const confirmDiagnosisModel = (id, modelId) =>
  api.post(`/api/diagnosis/sessions/${id}/model`, { model_id: modelId })
export const closeDiagnosis = (id, data) =>
  api.post(`/api/diagnosis/sessions/${id}/close`, data)
export const getDiagnosisSummary = (id) => api.get(`/api/diagnosis/sessions/${id}/summary`)