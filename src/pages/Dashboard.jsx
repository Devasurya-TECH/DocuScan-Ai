import { ArrowRight, CheckCircle2, FileText, Plus, UploadCloud } from 'lucide-react'
import { Link } from 'react-router-dom'
import DocumentTable from '../components/DocumentTable'
import { useI18n } from '../i18n'
import { useDocuments } from '../hooks/useDocuments'

export default function Dashboard() {
  const { t } = useI18n()
  const { documents, loading, error } = useDocuments()
  const completed = documents.filter((d) => d.status === 'completed').length

  return (
    <div className="space-y-6">
      {/* Welcome / Action Card */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-850 to-slate-950 p-6 text-white shadow-xl sm:p-8 dark:from-[#0a1622] dark:via-[#09151f] dark:to-[#060e15]">
        <div className="relative z-10 flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div className="max-w-xl space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-xs font-semibold text-teal-300">
              docTR Neural Engine Active
            </span>
            <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl text-white">
              Document Text Extraction & Conversion
            </h1>
            <p className="text-sm leading-relaxed text-slate-300">
              Upload scanned documents, photos, or multi-page PDFs to extract full text, make edits, and download editable DOCX, TXT, or searchable PDF files.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/scan"
              className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-teal-600/30 transition hover:-translate-y-0.5 hover:bg-teal-500"
            >
              <UploadCloud size={18} />
              <span>Extract Text from Document</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>

        {/* Subtle metrics */}
        <div className="relative z-10 mt-6 grid grid-cols-2 gap-3 border-t border-white/10 pt-6 sm:grid-cols-2 max-w-md">
          <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 backdrop-blur-xs">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-teal-500/20 text-teal-300">
              <FileText size={18} />
            </span>
            <div>
              <p className="text-xl font-extrabold text-white">{loading ? '…' : documents.length}</p>
              <p className="text-xs text-slate-400">Total Documents</p>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-xl bg-white/5 p-3 backdrop-blur-xs">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-500/20 text-emerald-300">
              <CheckCircle2 size={18} />
            </span>
            <div>
              <p className="text-xl font-extrabold text-white">{loading ? '…' : completed}</p>
              <p className="text-xs text-slate-400">Successfully Processed</p>
            </div>
          </div>
        </div>
      </section>

      {/* Recent Documents Section */}
      <section className="rounded-2xl border border-slate-200/80 bg-white overflow-hidden shadow-xs dark:border-slate-800 dark:bg-[#0c1824]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Recent Documents</h2>
            <p className="text-xs text-slate-500">View extracted text and export documents</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/scan"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <Plus size={14} />
              <span>New Document</span>
            </Link>
            <Link
              to="/documents"
              className="inline-flex items-center gap-1 text-xs font-bold text-teal-600 hover:text-teal-700 dark:text-teal-400"
            >
              <span>{t('viewAll')}</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>

        {error ? (
          <p className="m-5 rounded-xl bg-rose-50 p-4 text-sm font-medium text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
            {error}
          </p>
        ) : (
          <DocumentTable documents={documents.slice(0, 10)} />
        )}
      </section>
    </div>
  )
}
