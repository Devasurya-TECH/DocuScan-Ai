import { FileScan, Gauge, History, Settings, UploadCloud, Files, X, ChevronRight } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', icon: Gauge, end: true },
  { to: '/scan', label: 'New scan', icon: UploadCloud },
  { to: '/documents', label: 'Documents', icon: Files },
  { to: '/history', label: 'OCR history', icon: History },
]

export default function Sidebar({ open, close }) {
  return <aside className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-slate-200/80 bg-white px-4 py-5 transition-transform duration-300 dark:border-slate-800 dark:bg-[#101827] ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
    <div className="mb-10 flex items-center justify-between px-2"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-200 dark:shadow-none"><FileScan size={21} /></span><span className="text-lg font-bold tracking-tight">DocuScan <em className="not-italic text-indigo-600">AI</em></span></div><button onClick={close} aria-label="Close navigation" className="p-2 text-slate-400 lg:hidden"><X size={20} /></button></div>
    <nav className="space-y-1" aria-label="Main navigation">{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={close} className={({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'}`}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
    <div className="mt-auto space-y-3"><NavLink to="/settings" onClick={close} className={({isActive}) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium ${isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-500 dark:text-slate-400'}`}><Settings size={18} />Settings</NavLink><div className="rounded-2xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900/60"><div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">DS</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-700 dark:text-slate-200">DocuScan workspace</p><p className="text-xs text-slate-400">Local project</p></div><ChevronRight size={16} className="text-slate-400" /></div></div></div>
  </aside>
}
