import { ArrowRight, FileSearch, FileText, Download, Sparkles, UploadCloud } from 'lucide-react'
import { Link } from 'react-router-dom'

const steps = [
  {
    icon: UploadCloud,
    title: 'Upload',
    desc: 'Drop any photo, scan, or PDF — even blurry or tilted ones.',
    color: 'bg-teal-500/10 text-teal-500',
  },
  {
    icon: FileSearch,
    title: 'Extract',
    desc: 'AI reads every word with docTR neural OCR — no account needed.',
    color: 'bg-violet-500/10 text-violet-500',
  },
  {
    icon: Sparkles,
    title: 'Auto-Fix',
    desc: 'One click corrects OCR typos and noise automatically.',
    color: 'bg-amber-500/10 text-amber-500',
  },
  {
    icon: Download,
    title: 'Download',
    desc: 'Get a searchable Sandwich PDF, structured DOCX, or plain TXT.',
    color: 'bg-emerald-500/10 text-emerald-500',
  },
]

export default function Dashboard() {
  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-850 to-slate-950 p-8 text-white shadow-xl sm:p-12 dark:from-[#0a1622] dark:via-[#09151f] dark:to-[#060e15]">
        {/* Glow blobs */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-teal-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-violet-500/10 blur-3xl" />

        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="max-w-xl space-y-4">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-xs font-semibold text-teal-300">
              <Sparkles size={12} /> docTR Neural OCR — No sign-up required
            </span>
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Turn any document photo<br className="hidden sm:block" /> into editable text
            </h1>
            <p className="text-sm leading-relaxed text-slate-300">
              Upload a scanned document, receipt, handwritten note, or multi-page PDF.
              DocuScan AI extracts all text, auto-corrects OCR errors, and lets you
              download a Sandwich PDF (image + searchable text) or a structured Word file.
              <strong className="text-white"> Free. No login. No data stored.</strong>
            </p>
          </div>

          <Link
            to="/scan"
            className="inline-flex shrink-0 items-center gap-2 rounded-2xl bg-teal-600 px-7 py-4 text-sm font-bold text-white shadow-xl shadow-teal-600/30 transition hover:-translate-y-0.5 hover:bg-teal-500"
          >
            <UploadCloud size={20} />
            <span>Start Scanning</span>
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section>
        <h2 className="mb-5 text-sm font-extrabold uppercase tracking-widest text-teal-600 dark:text-teal-400">
          How it works
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(({ icon: Icon, title, desc, color }, i) => (
            <div
              key={title}
              className="relative rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-[#0c1824]"
            >
              <span className="absolute right-4 top-4 text-2xl font-black text-slate-100 dark:text-slate-800">
                0{i + 1}
              </span>
              <span className={`mb-4 inline-grid h-11 w-11 place-items-center rounded-xl ${color}`}>
                <Icon size={22} />
              </span>
              <h3 className="mb-1 font-extrabold text-slate-900 dark:text-slate-100">{title}</h3>
              <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Export formats */}
      <section>
        <h2 className="mb-5 text-sm font-extrabold uppercase tracking-widest text-teal-600 dark:text-teal-400">
          Export formats
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            {
              label: 'Sandwich PDF',
              tag: '.PDF',
              desc: 'Your original document image as background with an invisible text layer on top — looks identical to the scan, but every word is selectable, searchable, and copyable.',
              color: 'border-teal-500/40 bg-teal-50/50 dark:bg-teal-950/20',
            },
            {
              label: 'Structured Word',
              tag: '.DOCX',
              desc: 'Native Word tables, headings, and tab-stop key-value pairs reconstructed from the detected layout — fully editable in Microsoft Word or Google Docs.',
              color: 'border-violet-500/40 bg-violet-50/50 dark:bg-violet-950/20',
            },
            {
              label: 'Plain Text',
              tag: '.TXT',
              desc: 'Clean UTF-8 text dump of your corrected document content, ready to paste anywhere.',
              color: 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/60',
            },
          ].map(({ label, tag, desc, color }) => (
            <div key={label} className={`rounded-2xl border p-5 ${color}`}>
              <div className="mb-2 flex items-center gap-2">
                <FileText size={16} className="text-teal-600 dark:text-teal-400" />
                <span className="font-extrabold text-slate-900 dark:text-slate-100">{label}</span>
                <code className="ml-auto rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {tag}
                </code>
              </div>
              <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA bottom */}
      <div className="flex justify-center pb-4">
        <Link
          to="/scan"
          className="inline-flex items-center gap-2 rounded-2xl bg-teal-600 px-8 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-600/25 transition hover:-translate-y-0.5 hover:bg-teal-500"
        >
          <UploadCloud size={18} />
          Upload your first document →
        </Link>
      </div>
    </div>
  )
}
