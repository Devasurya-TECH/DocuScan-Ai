import { Activity, CheckCircle2, FileText, UploadCloud, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import StatCard from '../components/StatCard'
import DocumentTable from '../components/DocumentTable'
import { useDocuments } from '../hooks/useDocuments'

export default function Dashboard() {
  const { documents, loading, error } = useDocuments()
  const completed = documents.filter((d) => d.status === 'completed').length
  const failed = documents.filter((d) => d.status === 'failed').length
  const scores = documents.map((d) => Number(d.average_confidence)).filter(Number.isFinite)
  const confidence = scores.length ? `${Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100)}%` : '—'
  return <div className="space-y-7"><section className="relative overflow-hidden rounded-3xl bg-[#111b36] px-6 py-7 text-white shadow-xl shadow-indigo-950/10 sm:px-8 sm:py-9"><div className="absolute -right-16 -top-20 h-56 w-56 rounded-full bg-indigo-500/25 blur-3xl"/><div className="relative max-w-2xl"><span className="inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-indigo-100">Intelligent document workspace</span><h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">Turn paper documents into usable data.</h2><p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">Upload a document image and DocuScan AI will correct, enhance, and extract its text.</p><Link to="/scan" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-indigo-50"><UploadCloud size={17}/>Scan a document</Link></div></section><section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="Documents scanned" value={loading ? '…' : documents.length} helper="Stored in your API" icon={FileText}/><StatCard label="Successfully processed" value={loading ? '…' : completed} helper="Completed OCR scans" icon={CheckCircle2} tone="emerald"/><StatCard label="Failed scans" value={loading ? '…' : failed} helper="Reported by the API" icon={XCircle} tone="rose"/><StatCard label="OCR confidence" value={confidence} helper={scores.length ? 'Average across scans' : 'No OCR text yet'} icon={Activity} tone="violet"/></section><section><div className="mb-4 flex items-end justify-between"><div><h2 className="text-lg font-bold tracking-tight">Recent documents</h2><p className="mt-1 text-sm text-slate-500">Live records from the connected API.</p></div><Link className="text-sm font-semibold text-indigo-600" to="/documents">View all</Link></div>{error ? <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : <DocumentTable documents={documents.slice(0, 5)} />}</section></div>
}
