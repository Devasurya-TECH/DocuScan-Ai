import {
  ArrowRight,
  Download,
  FileSearch,
  FileScan,
  FileText,
  LogIn,
  Sparkles,
  UploadCloud,
  UserPlus,
} from 'lucide-react'
import { Link } from 'react-router-dom'

const FEATURES = [
  {
    icon: UploadCloud,
    title: 'Upload',
    desc: 'Drop any photo, scan, or PDF — even blurry or tilted documents.',
    color: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
  },
  {
    icon: FileSearch,
    title: 'Extract',
    desc: 'High-accuracy OCR reads every word with precision across layouts.',
    color: 'bg-violet-500/10 text-violet-600 dark:text-violet-400',
  },
  {
    icon: Sparkles,
    title: 'Auto-Fix',
    desc: 'One click corrects OCR typos, noise, and common recognition errors.',
    color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  {
    icon: Download,
    title: 'Export',
    desc: 'Download a Sandwich PDF, structured DOCX, or plain TXT file.',
    color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  },
]

const FORMATS = [
  {
    label: 'Sandwich PDF',
    tag: '.PDF',
    desc: 'Your original document image with an invisible searchable text layer — looks identical to the scan, every word selectable and copyable.',
    accent: 'border-teal-500/30 bg-teal-50/50 dark:bg-teal-950/20',
  },
  {
    label: 'Structured Word',
    tag: '.DOCX',
    desc: 'Native Word tables, headings, and key-value pairs reconstructed from the detected layout — fully editable in Microsoft Word or Google Docs.',
    accent: 'border-violet-500/30 bg-violet-50/50 dark:bg-violet-950/20',
  },
  {
    label: 'Plain Text',
    tag: '.TXT',
    desc: 'Clean UTF-8 text dump of your corrected document content, ready to paste anywhere.',
    accent: 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/60',
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-[#07111a]">
      {/* ── Top Nav ── */}
      <header className="sticky top-0 z-20 border-b border-slate-200/60 bg-[#f8fafc]/90 backdrop-blur-xl dark:border-slate-800/60 dark:bg-[#07111a]/90">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/25 transition group-hover:bg-teal-700">
              <FileScan size={18} />
            </span>
            <span className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">
              DocuScan <em className="not-italic text-teal-600 dark:text-teal-400">AI</em>
            </span>
          </Link>

          {/* Auth links */}
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/login"
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 transition hover:border-teal-400 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-500 dark:hover:text-teal-400"
            >
              <LogIn size={14} />
              <span>Sign in</span>
            </Link>
            <Link
              to="/register"
              className="flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-2 text-xs font-bold text-white shadow-md shadow-teal-600/20 transition hover:bg-teal-700"
            >
              <UserPlus size={14} />
              <span className="hidden sm:inline">Create account</span>
              <span className="sm:hidden">Sign up</span>
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        {/* ── Hero ── */}
        <section className="py-20 sm:py-28">
          <div className="max-w-2xl">
            <span className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-xs font-semibold text-teal-600 dark:text-teal-400">
              <Sparkles size={12} />
              Production-Grade OCR Engine
            </span>
            <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl dark:text-white">
              Turn any document photo<br className="hidden sm:block" />
              into editable text
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-500 dark:text-slate-400">
              Upload a scanned document, receipt, handwritten note, or multi-page PDF.
              DocuScan AI extracts all text, auto-corrects OCR errors, and lets you
              download a Sandwich PDF, structured Word file, or plain text.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/register"
                className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-600/25 transition hover:-translate-y-0.5 hover:bg-teal-500"
              >
                <UserPlus size={18} />
                Get started free
                <ArrowRight size={16} />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-6 py-3.5 text-sm font-bold text-slate-700 transition hover:border-teal-400 hover:text-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-500"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>

        {/* ── How it works ── */}
        <section className="pb-20">
          <h2 className="mb-8 text-xs font-extrabold uppercase tracking-widest text-teal-600 dark:text-teal-400">
            How it works
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, desc, color }, i) => (
              <div
                key={title}
                className="relative rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824]"
              >
                <span className="absolute right-4 top-4 text-2xl font-black text-slate-100 dark:text-slate-800 select-none">
                  0{i + 1}
                </span>
                <span className={`mb-4 inline-grid h-11 w-11 place-items-center rounded-xl ${color}`}>
                  <Icon size={22} />
                </span>
                <h3 className="mb-1 font-extrabold text-slate-900 dark:text-slate-100">
                  {title}
                </h3>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Export formats ── */}
        <section className="pb-20">
          <h2 className="mb-8 text-xs font-extrabold uppercase tracking-widest text-teal-600 dark:text-teal-400">
            Export formats
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {FORMATS.map(({ label, tag, desc, accent }) => (
              <div key={label} className={`rounded-2xl border p-5 ${accent}`}>
                <div className="mb-3 flex items-center gap-2">
                  <FileText size={16} className="text-teal-600 dark:text-teal-400" />
                  <span className="font-extrabold text-slate-900 dark:text-slate-100">
                    {label}
                  </span>
                  <code className="ml-auto rounded bg-slate-200/80 px-1.5 py-0.5 text-[10px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    {tag}
                  </code>
                </div>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Bottom CTA ── */}
        <section className="mb-20 rounded-3xl bg-gradient-to-br from-slate-900 to-slate-950 p-10 text-center shadow-xl dark:from-[#0a1622] dark:to-[#060e15]">
          <h2 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            Ready to extract your first document?
          </h2>
          <p className="mt-3 text-sm text-slate-400">
            Create a free account and start processing documents in seconds.
          </p>
          <Link
            to="/register"
            className="mt-7 inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-500"
          >
            <UserPlus size={18} />
            Create free account
            <ArrowRight size={16} />
          </Link>
        </section>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 dark:border-slate-800/60">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 py-8 text-xs text-slate-400 sm:flex-row sm:px-8">
          <div className="flex items-center gap-2">
            <FileScan size={14} className="text-teal-600" />
            <span className="font-bold text-slate-600 dark:text-slate-300">DocuScan AI</span>
            <span>· AI Document Intelligence</span>
          </div>
          <span>© {new Date().getFullYear()} DocuScan AI. All rights reserved.</span>
        </div>
      </footer>
    </div>
  )
}
