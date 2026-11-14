import { Files, History, Plus, Search, SlidersHorizontal, UploadCloud } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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

  const filtered = useMemo(() => {
    return documents.filter((doc) => {
      const matchText = `${doc.filename} ${doc.extracted_text || ''} ${doc.document_type || ''}`
        .toLowerCase()
        .includes(query.toLowerCase())
      return matchText && (status === 'all' || doc.status === status)
    })
  }, [documents, query, status])

  const remove = async (doc) => {
    if (!window.confirm(`Delete ${doc.filename}?`)) return
    setDeleting(String(doc.id))
    try {
      await deleteDocument(doc.id)
      setDocuments((items) => items.filter((item) => item.id !== doc.id))
    } catch (err) {
      alert(`Failed to delete document: ${err.message}`)
    } finally {
      setDeleting('')
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/20">
            {history ? <History size={20} /> : <Files size={20} />}
          </span>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl dark:text-white">
              {history ? t('history') : t('documentLibrary')}
            </h1>
            <p className="text-xs text-slate-500">
              {history ? 'Completed and in-progress OCR records.' : t('documentLibraryHint')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {filtered.length} {t('documents').toLowerCase()}
          </span>
          <Link
            to="/scan"
            className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-teal-600/20 transition hover:bg-teal-500"
          >
            <UploadCloud size={15} />
            <span>Extract Text</span>
          </Link>
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200/80 bg-white overflow-hidden shadow-xs dark:border-slate-800 dark:bg-[#0c1824]">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center dark:border-slate-800">
          <label className="flex h-10 flex-1 items-center gap-2 rounded-xl bg-slate-50 px-3 text-slate-400 focus-within:ring-2 focus-within:ring-teal-500/20 dark:bg-slate-900">
            <Search size={16} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('searchDocuments')}
              className="w-full bg-transparent text-xs font-medium text-slate-700 outline-none placeholder:text-slate-400 dark:text-slate-200"
            />
          </label>

          <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3 text-xs font-bold text-slate-600 dark:border-slate-700 dark:text-slate-300">
            <SlidersHorizontal size={15} />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="bg-transparent outline-none cursor-pointer"
            >
              <option value="all">{t('allStatus')}</option>
              <option value="completed">{t('completed')}</option>
              <option value="processing">{t('processing')}</option>
              <option value="failed">{t('failed')}</option>
            </select>
          </label>
        </div>

        {error ? (
          <p className="m-5 rounded-xl bg-rose-50 p-4 text-xs font-semibold text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
            {error}
          </p>
        ) : loading ? (
          <div className="space-y-3 p-5">
            <div className="h-14 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
            <div className="h-14 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />
          </div>
        ) : (
          <DocumentTable documents={filtered} history={history} onDelete={deleting ? undefined : remove} />
        )}
      </section>
    </div>
  )
}
