import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  Clock,
  Files,
  FileText,
  Loader2,
  ScanText,
  UploadCloud,
  XCircle,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useDocuments } from '../hooks/useDocuments'
import { useI18n } from '../i18n'

function StatCard({ icon: Icon, label, value, accent }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824]">
      <span
        className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${accent}`}
      >
        <Icon size={20} />
      </span>
      <div>
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{label}</p>
        <p className="mt-0.5 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {value}
        </p>
      </div>
    </div>
  )
}

function RecentDocRow({ doc }) {
  const statusIcon = {
    completed: <CheckCircle2 size={14} className="text-emerald-500" />,
    processing: <Loader2 size={14} className="animate-spin text-teal-500" />,
    failed: <XCircle size={14} className="text-rose-500" />,
  }
  const statusLabel = {
    completed: 'Completed',
    processing: 'Processing',
    failed: 'Failed',
  }
  return (
    <Link
      to={`/documents/${doc.id}`}
      className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-slate-50 dark:hover:bg-slate-800/60"
    >
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-teal-50 text-teal-600 dark:bg-teal-950/40 dark:text-teal-400">
        <FileText size={16} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
          {doc.filename || doc.title || `Document ${doc.id}`}
        </p>
        <p className="text-xs text-slate-400">
          {doc.created_at
            ? new Date(doc.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : '—'}
        </p>
      </div>
      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
        {statusIcon[doc.status] || null}
        <span className="hidden sm:inline">
          {statusLabel[doc.status] || doc.status}
        </span>
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const { t } = useI18n()
  const { documents, loading, error } = useDocuments()

  const stats = useMemo(() => {
    const total = documents.length
    const completed = documents.filter((d) => d.status === 'completed').length
    const processing = documents.filter((d) => d.status === 'processing').length
    const failed = documents.filter((d) => d.status === 'failed').length
    return { total, completed, processing, failed }
  }, [documents])

  const recent = useMemo(
    () =>
      [...documents]
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 6),
    [documents]
  )

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <p className="text-xs font-extrabold uppercase tracking-widest text-teal-600 dark:text-teal-400">
          {t('workspace')}
        </p>
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
          Welcome back{user?.username ? `, ${user.username}` : ''}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Here's an overview of your document workspace.
        </p>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          to="/scan"
          className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-teal-600/20 transition hover:bg-teal-700"
        >
          <UploadCloud size={17} />
          New Scan
        </Link>
        <Link
          to="/documents"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:border-teal-400 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-500"
        >
          <Files size={17} />
          My Documents
        </Link>
      </div>

      {/* Stats */}
      <section>
        <h2 className="mb-4 text-xs font-extrabold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          Overview
        </h2>
        {loading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              icon={ScanText}
              label="Total Documents"
              value={stats.total}
              accent="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            />
            <StatCard
              icon={CheckCircle2}
              label="Completed"
              value={stats.completed}
              accent="bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400"
            />
            <StatCard
              icon={Clock}
              label="Processing"
              value={stats.processing}
              accent="bg-teal-50 text-teal-600 dark:bg-teal-500/10 dark:text-teal-400"
            />
            <StatCard
              icon={XCircle}
              label="Failed"
              value={stats.failed}
              accent="bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400"
            />
          </div>
        )}
      </section>

      {/* Recent documents */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-slate-500 dark:text-slate-400">
            Recent Documents
          </h2>
          <Link
            to="/documents"
            className="text-xs font-bold text-teal-600 hover:underline dark:text-teal-400"
          >
            View all →
          </Link>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-[#0c1824]">
          {loading ? (
            <div className="space-y-2 p-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-12 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800"
                />
              ))}
            </div>
          ) : error ? (
            <p className="p-5 text-xs font-semibold text-rose-600 dark:text-rose-400">
              {error}
            </p>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <span className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-50 text-teal-600 dark:bg-teal-950/40 dark:text-teal-400">
                <ScanText size={24} />
              </span>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                No documents yet
              </p>
              <p className="text-xs text-slate-400">
                Upload a receipt, invoice, form, or printed page to get started.
              </p>
              <Link
                to="/scan"
                className="mt-2 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-teal-700"
              >
                <UploadCloud size={15} />
                Start your first scan
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 p-2 dark:divide-slate-800">
              {recent.map((doc) => (
                <RecentDocRow key={doc.id} doc={doc} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
