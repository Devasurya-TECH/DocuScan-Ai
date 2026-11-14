import { Globe2, Moon, Sun } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useI18n } from '../i18n'

export default function Navbar({ theme, setTheme }) {
  const { pathname } = useLocation()
  const { language, setLanguage, languages, t } = useI18n()

  const names = {
    '/': 'Home',
    '/scan': t('newDocument'),
    '/settings': t('settings'),
  }
  const title = names[pathname] || t('document')

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
      </div>
    </header>
  )
}
