import { useCallback, useEffect, useState } from 'react'
import { listDocuments } from '../services/documentService'
import { normalizeDocument } from '../utils/documents'

export function useDocuments() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      setDocuments((await listDocuments()).map(normalizeDocument))
      setError('')
    } catch {
      setError('Document history is unavailable. Check that the Django API is running.')
    } finally { setLoading(false) }
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { documents, loading, error, refresh, setDocuments }
}
