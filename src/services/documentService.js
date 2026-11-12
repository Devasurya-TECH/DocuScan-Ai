import api from './api'

export async function uploadDocument(file, onUploadProgress) {
  const data = new FormData()
  data.append('uploaded_file', file)
  const response = await api.post('/documents/upload/', data, { onUploadProgress })
  return response.data
}

export async function checkApiHealth() {
  const response = await api.get('/health/')
  return response.data
}

export async function listDocuments() {
  const response = await api.get('/documents/')
  return Array.isArray(response.data) ? response.data : response.data.results || []
}

export async function getDocument(id) {
  const response = await api.get(`/documents/${id}/`)
  return response.data
}

export async function deleteDocument(id) {
  await api.delete(`/documents/${id}/`)
}

export async function exportDocument(id, format, reconstructionMode) {
  const response = await api.post(`/documents/${id}/export/`, {
    format,
    reconstruction_mode: reconstructionMode,
  })
  return response.data
}

export function resolveImageUrl(value) {
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  return value.startsWith('/') ? value : `/${value}`
}
