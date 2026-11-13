import { Activity, ArrowUpRight, CheckCircle2, FileText, ScanLine, UploadCloud, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import DocumentTable from '../components/DocumentTable'
import StatCard from '../components/StatCard'
import { useI18n } from '../i18n'
import { useDocuments } from '../hooks/useDocuments'

export default function Dashboard() {
  const { t } = useI18n()
  const { documents, loading, error } = useDocuments()
  const completed = documents.filter((d) => d.status === 'completed').length
  const failed = documents.filter((d) => d.status === 'failed').length
  const scores = documents.map((d) => Number(d.average_confidence)).filter(Number.isFinite)
  const confidence = scores.length ? `${Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100)}%` : '—'
  return <div className="space-y-7">
    <section className="relative overflow-hidden rounded-[2rem] bg-slate-950 px-6 py-8 text-white shadow-2xl shadow-slate-950/15 sm:px-9 sm:py-10"><div className="absolute inset-0 bg-[radial-gradient(circle_at_90%_10%,rgba(99,102,241,.45),transparent_32%),radial-gradient(circle_at_72%_75%,rgba(168,85,247,.22),transparent_26%)]" /><div className="relative grid gap-8 lg:grid-cols-[1.5fr_.75fr] lg:items-end"><div className="max-w-2xl"><span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-indigo-100"><ScanLine size={14} />{t('intelligentWorkspace')}</span><h2 className="mt-5 text-3xl font-extrabold tracking-tight sm:text-4xl">{t('heroTitle')}</h2><p className="mt-4 max-w-xl text-sm leading-7 text-slate-300 sm:text-base">{t('heroText')}</p><Link to="/scan" className="mt-7 inline-flex items-center gap-2 rounded-2xl bg-white px-5 py-3 text-sm font-extrabold text-slate-950 shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:bg-indigo-50"><UploadCloud size={18} />{t('scanDocument')}<ArrowUpRight size={16} /></Link></div><div className="grid grid-cols-2 gap-3 rounded-3xl border border-white/10 bg-white/[.06] p-4 backdrop-blur-sm"><Metric value={loading ? '…' : documents.length} label={t('documentsScanned')} /><Metric value={loading ? '…' : confidence} label={t('confidence')} /></div></div></section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label={t('documentsScanned')} value={loading ? '…' : documents.length} helper={t('localWorkspace')} icon={FileText} /><StatCard label={t('processed')} value={loading ? '…' : completed} helper="OCR complete" icon={CheckCircle2} tone="emerald" /><StatCard label={t('failed')} value={loading ? '…' : failed} helper="Review errors" icon={XCircle} tone="rose" /><StatCard label={t('confidence')} value={confidence} helper={scores.length ? 'Across completed scans' : t('noText')} icon={Activity} tone="violet" /></section>
    <section className="surface-card overflow-hidden"><div className="flex flex-wrap items-end justify-between gap-3 border-b border-slate-100 px-5 py-5 sm:px-6 dark:border-slate-800"><div><p className="text-[11px] font-extrabold uppercase tracking-[.15em] text-indigo-500">{t('workspace')}</p><h2 className="mt-1 text-lg font-extrabold tracking-tight">{t('recentDocuments')}</h2><p className="mt-1 text-sm text-slate-500">Your latest processing activity, directly from the API.</p></div><Link className="inline-flex items-center gap-1 text-sm font-extrabold text-indigo-600" to="/documents">{t('viewAll')} <ArrowUpRight size={16} /></Link></div>{error ? <p className="m-5 rounded-2xl bg-rose-50 p-4 text-sm font-medium text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">{error}</p> : <DocumentTable documents={documents.slice(0, 5)} />}</section>
  </div>
}

function Metric({ value, label }) { return <div className="rounded-2xl bg-black/15 p-4"><p className="text-2xl font-extrabold">{value}</p><p className="mt-1 text-[11px] font-semibold leading-4 text-slate-300">{label}</p></div> }
