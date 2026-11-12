import { Files, History } from 'lucide-react'
import { useState } from 'react'
import DocumentTable from '../components/DocumentTable'
import { useDocuments } from '../hooks/useDocuments'
import { deleteDocument } from '../services/documentService'

export default function Documents({ history = false }) {
  const { documents, loading, error, setDocuments } = useDocuments()
  const [deleting, setDeleting] = useState('')
  const remove = async (doc) => {
    if (!window.confirm(`Delete ${doc.filename}?`)) return
    setDeleting(String(doc.id))
    try { await deleteDocument(doc.id); setDocuments((items) => items.filter((item) => item.id !== doc.id)) } finally { setDeleting('') }
  }
  return <div><div className="mb-7 flex items-start gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15">{history ? <History size={20}/> : <Files size={20}/>}</span><div><h2 className="text-2xl font-bold tracking-tight">{history ? 'OCR history' : 'Your documents'}</h2><p className="mt-1 text-sm text-slate-500">{history ? 'Completed and in-progress OCR records from the API.' : 'Every document stored in this workspace.'}</p></div></div>{error ? <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : loading ? <p className="text-sm text-slate-500">Loading documents…</p> : <DocumentTable documents={documents} history onDelete={deleting ? undefined : remove} />}</div>
}
