const storageKey = 'docuscan-recent-documents'

export function recentDocuments() {
  try { return JSON.parse(localStorage.getItem(storageKey) || '[]') } catch { return [] }
}

export function rememberDocument(response, fallbackName) {
  const item = {
    id: response.id ?? `local-${Date.now()}`,
    filename: response.uploaded_file?.split('/').pop() || fallbackName,
    status: response.status || 'uploaded',
    created_at: response.created_at || new Date().toISOString(),
    uploaded_file: response.uploaded_file || '',
    extracted_text: response.extracted_text || '',
    processed_file: response.processed_file || '',
    ocr_results: response.ocr_results || [],
    average_confidence: response.average_confidence ?? null,
    source: 'upload',
  }
  const next = [item, ...recentDocuments().filter((doc) => String(doc.id) !== String(item.id))].slice(0, 12)
  localStorage.setItem(storageKey, JSON.stringify(next))
  return item
}

export function normalizeDocument(response) {
  return {
    ...response,
    filename: response.uploaded_file?.split('/').pop() || `Document ${response.id}`,
    extracted_text: response.extracted_text || '',
    processed_file: response.processed_file || '',
    ocr_results: response.ocr_results || [],
    average_confidence: response.average_confidence ?? null,
  }
}

export function findRecentDocument(id) {
  return recentDocuments().find((doc) => String(doc.id) === String(id))
}

export const friendlyStatus = (status) => status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown'

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
