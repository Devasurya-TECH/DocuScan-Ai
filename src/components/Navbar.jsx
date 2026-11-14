import { Globe2, LogOut, Menu, Moon, Sun } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useAuth } from '../context/AuthContext'

const PAGE_TITLES = {
  '/dashboard':  'Dashboard',
  '/scan':       'New Scan',
  '/documents':  'My Documents',
  '/settings':   'Settings',
}

export default function Navbar({ theme, setTheme, onMenu }) {
  const { pathname } = useLocation()
  const { language, setLanguage, languages, t } = useI18n()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // For document detail pages, show a generic title
  const isDocDetail = /^\/documents\/\d+/.test(pathname)
  const title = isDocDetail ? 'Document Editor' : (PAGE_TITLES[pathname] || 'DocuScan AI')

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 flex min-h-[64px] items-center justify-between border-b border-slate-200/80 bg-[#f8fafc]/90 px-4 backdrop-blur-xl sm:px-6 lg:px-9 dark:border-slate-800 dark:bg-[#07111a]/90">
      {/* Mobile menu button + Page title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          aria-label="Open navigation"
          onClick={onMenu}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 lg:hidden dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          <Menu size={18} />
        </button>
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-teal-600">
            {t('workspace')}
          </p>
          <h1 className="truncate text-base font-extrabold tracking-tight sm:text-lg">
            {title}
          </h1>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Language selector */}
        <label className="relative hidden items-center sm:flex">
          <Globe2 size={15} className="pointer-events-none absolute left-3 text-slate-400" />
          <select
            aria-label={t('language')}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="h-9 appearance-none rounded-xl border border-slate-200 bg-white py-0 pl-8 pr-3 text-xs font-bold text-slate-600 outline-none transition hover:border-teal-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
          >
            {languages.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        {/* Theme toggle */}
        <button
          type="button"
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="grid h-9 w-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-teal-400 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-amber-400 dark:hover:border-amber-400"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* User chip + logout */}
        {user && (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="grid h-7 w-7 place-items-center rounded-xl bg-teal-600 text-xs font-extrabold text-white">
              {user.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <span className="hidden max-w-[100px] truncate text-xs font-bold text-slate-700 sm:inline dark:text-slate-200">
              {user.username}
            </span>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40"
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
