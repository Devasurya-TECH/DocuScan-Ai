import api from './api'

export async function uploadDocument(file, onUploadProgress, ocrLanguages = '') {
  const data = new FormData()
  data.append('uploaded_file', file)
  if (ocrLanguages) data.append('ocr_languages', ocrLanguages)
  const response = await api.post('/documents/upload/', data, { onUploadProgress })
  return response.data
}

export async function checkApiHealth() {
  const response = await api.get('/health/')
  return response.data
}

export async function listDocuments(params = {}) {
  const response = await api.get('/documents/', { params })
  return Array.isArray(response.data) ? response.data : response.data.results || []
}

export async function getDocument(id) {
  const response = await api.get(`/documents/${id}/`)
  return response.data
}

export async function pollDocumentStatus(id) {
  const response = await api.get(`/documents/${id}/status/`)
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

export async function saveDocumentCorrection(id, correctedText, verifiedFields = {}) {
  const response = await api.patch(`/documents/${id}/corrections/`, {
    corrected_text: correctedText,
    verified_fields: verifiedFields,
  })
  return response.data
}

export async function reprocessDocument(id) {
  const response = await api.post(`/documents/${id}/reprocess/`)
  return response.data
}

export async function autocorrectDocument(id, text) {
  const response = await api.post(`/documents/${id}/autocorrect/`, { text })
  return response.data
}

export async function askDocumentQuestion(id, question) {
  const response = await api.post(`/documents/${id}/ask/`, { question })
  return response.data
}

export async function getBenchmarkReport(split = 'development') {
  const response = await api.get('/benchmark/', { params: { split } })
  return response.data
}

const rawApiUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || ''
const hostBase = rawApiUrl ? rawApiUrl.replace(/\/api\/?$/, '').replace(/\/$/, '') : ''

export function resolveImageUrl(value) {
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  const cleanPath = value.startsWith('/') ? value : `/${value}`
  return hostBase ? `${hostBase}${cleanPath}` : cleanPath
}
