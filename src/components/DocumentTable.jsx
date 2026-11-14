import { ArrowRight, Eye, FileText, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { formatDate, friendlyStatus } from '../utils/documents'

export default function DocumentTable({ documents, history = false, onDelete }) {
  const { t } = useI18n()
  if (!documents.length) {
    return (
      <div className="px-6 py-14 text-center">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-teal-50 text-teal-600 dark:bg-teal-500/15">
          <FileText size={22} />
        </div>
        <h3 className="mt-4 font-extrabold text-slate-800 dark:text-slate-200">{t('noDocuments')}</h3>
        <p className="mt-1 text-xs text-slate-500">{t('noDocumentsHint')}</p>
        <Link
          to="/scan"
          className="mt-5 inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-teal-600/20 transition hover:bg-teal-500"
        >
          <span>{t('startScan')}</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    )
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[760px] text-left">
          <thead className="border-b border-slate-100 bg-slate-50/70 text-[11px] uppercase tracking-[.1em] text-slate-400 dark:border-slate-800 dark:bg-slate-900/40">
            <tr>
              <th className="px-6 py-3.5 font-extrabold">{t('document')}</th>
              <th className="px-5 py-3.5 font-extrabold">{t('status')}</th>
              <th className="px-5 py-3.5 font-extrabold">{t('uploaded')}</th>
              <th className="px-5 py-3.5 font-extrabold">{t('textPreview')}</th>
              <th className="px-5 py-3.5 text-right font-extrabold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {documents.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} onDelete={onDelete} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-slate-100 md:hidden dark:divide-slate-800">
        {documents.map((doc) => (
          <DocumentCard key={doc.id} doc={doc} onDelete={onDelete} />
        ))}
      </div>
      {history && (
        <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-400 dark:border-slate-800">
          Document list synchronized with DocuScan backend.
        </p>
      )}
    </>
  )
}

function DocumentRow({ doc, onDelete }) {
  const { t } = useI18n()
  return (
    <tr className="transition hover:bg-slate-50/70 dark:hover:bg-slate-900/40">
      <td className="px-6 py-4">
        <DocumentIdentity doc={doc} />
      </td>
      <td className="px-5 py-4">
        <Status status={doc.status} />
      </td>
      <td className="px-5 py-4 text-xs font-medium text-slate-500">{formatDate(doc.created_at)}</td>
      <td className="max-w-xs truncate px-5 py-4 text-xs text-slate-500 font-mono">
        {doc.extracted_text ? doc.extracted_text.slice(0, 80) : t('noText')}
      </td>
      <td className="px-5 py-4 text-right">
        <Actions doc={doc} onDelete={onDelete} />
      </td>
    </tr>
  )
}

function DocumentCard({ doc, onDelete }) {
  const { t } = useI18n()
  return (
    <article className="space-y-3 p-5">
      <div className="flex items-start justify-between gap-3">
        <DocumentIdentity doc={doc} />
        <Status status={doc.status} />
      </div>
      <p className="line-clamp-2 text-xs leading-5 text-slate-500 font-mono">
        {doc.extracted_text || t('noText')}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400">{formatDate(doc.created_at)}</span>
        <Actions doc={doc} onDelete={onDelete} />
      </div>
    </article>
  )
}

function DocumentIdentity({ doc }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-600 dark:bg-teal-500/15 dark:text-teal-400">
        <FileText size={18} />
      </span>
      <div className="min-w-0">
        <p className="max-w-56 truncate text-xs font-bold text-slate-900 dark:text-slate-100">{doc.filename}</p>
        <p className="mt-0.5 text-[10px] text-slate-400">ID #{doc.id}</p>
      </div>
    </div>
  )
}

function Status({ status }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
        status === 'completed'
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
          : status === 'failed'
            ? 'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300'
            : 'bg-teal-50 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300'
      }`}
    >
      {friendlyStatus(status)}
    </span>
  )
}

function Actions({ doc, onDelete }) {
  const { t } = useI18n()
  return (
    <span className="inline-flex items-center gap-1.5">
      <Link
        to={`/documents/${doc.id}`}
        aria-label={`${t('openDocument')} ${doc.filename}`}
        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-700 shadow-2xs transition hover:border-teal-500 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-teal-400 dark:hover:text-teal-300"
      >
        <Eye size={13} />
        <span>Open</span>
      </Link>
      {onDelete && (
        <button
          onClick={() => onDelete(doc)}
          aria-label={`${t('delete')} ${doc.filename}`}
          className="inline-grid h-7 w-7 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/15"
        >
          <Trash2 size={13} />
        </button>
      )}
    </span>
  )
}
