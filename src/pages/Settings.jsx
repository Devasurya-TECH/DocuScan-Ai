import { Check, Globe2, Languages, Moon, Palette, Server, Sun } from 'lucide-react'
import { useI18n } from '../i18n'

export default function Settings({ theme, setTheme }) {
  const { language, setLanguage, languages, t } = useI18n()

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <header>
        <p className="text-[11px] font-extrabold uppercase tracking-[.15em] text-teal-600">
          {t('workspace')}
        </p>
        <h2 className="mt-1 text-2xl font-extrabold tracking-tight">
          {t('settings')}
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Personalize the language and appearance of your document workspace.
        </p>
      </header>

      {/* Language */}
      <section className="surface-card p-5 sm:p-6">
        <div className="flex gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-teal-50 text-teal-700 dark:bg-teal-500/15">
            <Globe2 size={20} />
          </span>
          <div>
            <h3 className="font-extrabold">{t('language')}</h3>
            <p className="mt-1 text-sm leading-6 text-slate-500">{t('languageHint')}</p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {languages.map((item) => (
            <button
              key={item.code}
              onClick={() => setLanguage(item.code)}
              className={`flex items-center gap-3 rounded-2xl border p-4 text-left transition ${
                language === item.code
                  ? 'border-teal-500 bg-teal-50/70 shadow-sm dark:bg-teal-500/10'
                  : 'border-slate-200 hover:border-teal-200 dark:border-slate-700 dark:hover:border-teal-700'
              }`}
            >
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-teal-700 shadow-sm dark:bg-slate-800">
                <Languages size={18} />
              </span>
              <span className="flex-1 text-sm font-extrabold">{item.label}</span>
              {language === item.code && (
                <Check size={18} className="text-teal-700 dark:text-teal-400" />
              )}
            </button>
          ))}
        </div>
      </section>

      {/* Appearance */}
      <section className="surface-card p-5 sm:p-6">
        <div className="flex gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-slate-100 text-slate-700 dark:bg-slate-800">
            <Palette size={20} />
          </span>
          <div>
            <h3 className="font-extrabold">{t('appearance')}</h3>
            <p className="mt-1 text-sm leading-6 text-slate-500">{t('themeHint')}</p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {[
            ['light', t('lightMode'), Sun],
            ['dark', t('darkMode'), Moon],
          ].map(([value, label, Icon]) => (
            <button
              key={value}
              onClick={() => setTheme(value)}
              className={`flex items-center gap-3 rounded-2xl border p-4 text-left transition ${
                theme === value
                  ? 'border-teal-500 bg-teal-50/70 shadow-sm dark:bg-teal-500/10'
                  : 'border-slate-200 hover:border-teal-200 dark:border-slate-700 dark:hover:border-teal-700'
              }`}
            >
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-teal-700 shadow-sm dark:bg-slate-800">
                <Icon size={18} />
              </span>
              <span className="flex-1 text-sm font-extrabold">{label}</span>
              {theme === value && (
                <Check size={18} className="text-teal-700 dark:text-teal-400" />
              )}
            </button>
          ))}
        </div>
      </section>

      {/* Info note */}
      <section className="rounded-3xl border border-teal-100 bg-teal-50/60 p-5 dark:border-teal-500/20 dark:bg-teal-500/10">
        <div className="flex gap-3">
          <Server className="mt-0.5 shrink-0 text-teal-700 dark:text-teal-400" size={19} />
          <p className="text-sm leading-6 text-teal-950 dark:text-teal-100">
            The interface language above applies to this workspace only — it never
            translates or replaces your original OCR text. OCR recognition languages
            are configured on the scan page.
          </p>
        </div>
      </section>
    </div>
  )
}
