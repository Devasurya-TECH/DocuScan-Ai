import { ChevronRight, FileScan, Files, Gauge, History, Settings, UploadCloud, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useI18n } from '../i18n'

export default function Sidebar({ open, close }) {
  const { t } = useI18n()
  const links = [
    { to: '/', label: t('dashboard'), icon: Gauge, end: true },
    { to: '/scan', label: t('newScan'), icon: UploadCloud },
    { to: '/documents', label: t('documents'), icon: Files },
    { to: '/history', label: t('history'), icon: History },
  ]
  return <aside className={`fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col border-r border-slate-200/70 bg-white/95 px-4 py-5 shadow-2xl shadow-slate-900/5 backdrop-blur-xl transition-transform duration-300 dark:border-slate-800 dark:bg-[#0e1525]/95 lg:shadow-none ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
    <div className="mb-9 flex items-center justify-between px-2"><div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-500 text-white shadow-lg shadow-indigo-500/25"><FileScan size={22} /></span><div><span className="block text-lg font-extrabold tracking-tight">DocuScan <em className="not-italic text-indigo-600 dark:text-indigo-400">AI</em></span><span className="block text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">Intelligent documents</span></div></div><button onClick={close} aria-label="Close navigation" className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"><X size={19} /></button></div>
    <nav className="space-y-1.5" aria-label="Main navigation">{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={close} className={({ isActive }) => `group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'}`}><Icon size={18} strokeWidth={2.2} /><span>{label}</span></NavLink>)}</nav>
    <div className="mt-auto space-y-3"><NavLink to="/settings" onClick={close} className={({ isActive }) => `flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}`}><Settings size={18} />{t('settings')}</NavLink><div className="rounded-2xl bg-slate-950 p-3.5 text-white shadow-lg shadow-slate-950/10 dark:bg-slate-800"><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-xl bg-white/10 text-xs font-extrabold">DS</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">DocuScan AI</p><p className="text-xs text-slate-400">{t('localWorkspace')}</p></div><ChevronRight size={16} className="text-slate-500" /></div></div></div>
  </aside>
}
