import api from './index'

export function listDocuments(kbId) {
  return api.get(`/api/documents/list/${kbId}`)
}

export function uploadDocument(kbId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/api/documents/upload/${kbId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(docId) {
  return api.delete(`/api/documents/${docId}`)
}
