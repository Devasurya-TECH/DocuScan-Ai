import { FileScan } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Minimal layout for /login and /register.
 * No sidebar, no authenticated navbar — just a centered card on a gradient background.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#f8fafc] dark:bg-[#07111a]">
      {/* Minimal header */}
      <header className="flex h-16 items-center justify-between px-6 sm:px-10">
        <Link to="/" className="flex items-center gap-2.5 group">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-600 text-white shadow-md shadow-teal-600/25 transition group-hover:bg-teal-700">
            <FileScan size={18} />
          </span>
          <span className="text-sm font-extrabold tracking-tight text-slate-900 dark:text-white">
            DocuScan <em className="not-italic text-teal-600 dark:text-teal-400">AI</em>
          </span>
        </Link>
      </header>

      {/* Main content */}
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        {children}
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} DocuScan AI · AI Document Intelligence
      </footer>
    </div>
  )
}
