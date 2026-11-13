import { Files, History, Search, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import DocumentTable from '../components/DocumentTable'
import { useI18n } from '../i18n'
import { deleteDocument } from '../services/documentService'
import { useDocuments } from '../hooks/useDocuments'

export default function Documents({ history = false }) {
  const { t } = useI18n()
  const { documents, loading, error, setDocuments } = useDocuments()
  const [deleting, setDeleting] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const filtered = useMemo(() => documents.filter((doc) => {
    const matchText = `${doc.filename} ${doc.extracted_text || ''} ${doc.document_type || ''}`.toLowerCase().includes(query.toLowerCase())
    return matchText && (status === 'all' || doc.status === status)
  }), [documents, query, status])
  const remove = async (doc) => { if (!window.confirm(`Delete ${doc.filename}?`)) return; setDeleting(String(doc.id)); try { await deleteDocument(doc.id); setDocuments((items) => items.filter((item) => item.id !== doc.id)) } finally { setDeleting('') } }
  return <div className="space-y-6"><header className="flex flex-wrap items-end justify-between gap-4"><div className="flex items-start gap-3"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-500/25">{history ? <History size={21} /> : <Files size={21} />}</span><div><p className="text-[11px] font-extrabold uppercase tracking-[.15em] text-indigo-500">{t('workspace')}</p><h2 className="mt-1 text-2xl font-extrabold tracking-tight">{history ? t('history') : t('documentLibrary')}</h2><p className="mt-1 text-sm text-slate-500">{history ? 'Completed and in-progress OCR records.' : t('documentLibraryHint')}</p></div></div><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-extrabold text-slate-500 dark:bg-slate-800 dark:text-slate-300">{filtered.length} {t('documents').toLowerCase()}</span></header><section className="surface-card overflow-hidden"><div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:p-5 dark:border-slate-800"><label className="flex h-11 flex-1 items-center gap-2 rounded-xl bg-slate-50 px-3 text-slate-400 focus-within:ring-4 focus-within:ring-indigo-500/10 dark:bg-slate-900"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('searchDocuments')} className="w-full bg-transparent text-sm font-medium text-slate-700 outline-none placeholder:text-slate-400 dark:text-slate-200" /></label><label className="flex h-11 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-bold text-slate-500 dark:border-slate-700"><SlidersHorizontal size={16} /><select value={status} onChange={(event) => setStatus(event.target.value)} className="bg-transparent outline-none"><option value="all">{t('allStatus')}</option><option value="completed">{t('completed')}</option><option value="processing">{t('processing')}</option><option value="failed">{t('failed')}</option></select></label></div>{error ? <p className="m-5 rounded-2xl bg-rose-50 p-4 text-sm font-semibold text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">{error}</p> : loading ? <div className="space-y-3 p-5"><div className="h-16 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" /><div className="h-16 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" /></div> : <DocumentTable documents={filtered} history onDelete={deleting ? undefined : remove} />}</section></div>
}
