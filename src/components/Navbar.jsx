import { Globe2, Moon, Sun, User, LogOut, LogIn } from 'lucide-react'
import { useLocation, Link, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useAuth } from '../context/AuthContext'

export default function Navbar({ theme, setTheme }) {
  const { pathname } = useLocation()
  const { language, setLanguage, languages, t } = useI18n()
  const { user, isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const names = {
    '/': t('overview'),
    '/scan': t('newDocument'),
    '/documents': t('documents'),
    '/settings': t('settings'),
    '/login': 'Sign In',
    '/register': 'Register',
  }
  const title = names[pathname] || t('document')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-20 flex min-h-[72px] items-center justify-between border-b border-slate-200/80 bg-[#f8fafc]/90 px-4 backdrop-blur-xl sm:px-6 lg:px-9 dark:border-slate-800 dark:bg-[#07111a]/90">
      <div className="min-w-0">
        <p className="text-[10px] font-extrabold uppercase tracking-[.18em] text-teal-600">
          {t('workspace')}
        </p>
        <h1 className="truncate text-base font-extrabold tracking-tight sm:text-lg">{title}</h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Language selector */}
        <label className="relative hidden items-center sm:flex">
          <Globe2 size={16} className="pointer-events-none absolute left-3 text-slate-400" />
          <select
            aria-label={t('language')}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="h-10 appearance-none rounded-xl border border-slate-200 bg-white py-0 pl-9 pr-3 text-xs font-bold text-slate-600 outline-none transition hover:border-teal-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
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
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-xs transition hover:border-teal-400 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-amber-400 dark:hover:border-amber-400"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {/* User profile / Auth button */}
        {isAuthenticated && user ? (
          <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="grid h-7 w-7 place-items-center rounded-xl bg-teal-600 text-xs font-extrabold text-white">
              {user.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <span className="hidden text-xs font-bold text-slate-700 sm:inline dark:text-slate-200">
              {user.username}
            </span>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="rounded-lg p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-2 text-xs font-bold text-white shadow-md shadow-teal-600/20 transition hover:bg-teal-700"
          >
            <LogIn size={15} />
            <span>Sign in</span>
          </Link>
        )}
      </div>
    </header>
  )
}
