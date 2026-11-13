import { FileScan, Files, Gauge, Settings, UploadCloud, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useI18n } from '../i18n'

export default function Sidebar({ open, close }) {
  const { t } = useI18n()
  const links = [
    { to: '/', label: t('dashboard'), icon: Gauge, end: true },
    { to: '/scan', label: t('newScan'), icon: UploadCloud },
    { to: '/documents', label: t('documents'), icon: Files },
  ]
  return <aside className={`fixed inset-y-0 left-0 z-40 flex w-[280px] flex-col border-r border-slate-200/80 bg-white px-4 py-5 shadow-2xl shadow-slate-900/5 transition-transform duration-300 dark:border-slate-800 dark:bg-[#09151f] lg:shadow-none ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
    <div className="mb-9 flex items-center justify-between px-2"><div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-teal-600 text-white shadow-lg shadow-teal-600/20"><FileScan size={22} /></span><div><span className="block text-lg font-extrabold tracking-tight">DocuScan <em className="not-italic text-teal-600 dark:text-teal-400">AI</em></span><span className="block text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">Document intelligence</span></div></div><button onClick={close} aria-label="Close navigation" className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"><X size={19} /></button></div>
    <nav className="space-y-1.5" aria-label="Main navigation">{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={close} className={({ isActive }) => `group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-teal-600 text-white shadow-md shadow-teal-600/20' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'}`}><Icon size={18} strokeWidth={2.2} /><span>{label}</span></NavLink>)}</nav>
    <div className="mt-auto"><NavLink to="/settings" onClick={close} className={({ isActive }) => `flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${isActive ? 'bg-teal-50 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300' : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}`}><Settings size={18} />{t('settings')}</NavLink></div>
  </aside>
}
