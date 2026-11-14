import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Lock, User, ArrowRight, AlertCircle, KeyRound } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Respect ?next= param — fall back to /dashboard
  const params = new URLSearchParams(location.search)
  const next = params.get('next') || '/dashboard'

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    if (!username.trim() || !password) {
      setError('Please enter both username and password.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await login(username.trim(), password)
      navigate(next, { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Invalid username or password.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = () => {
    setUsername('demo')
    setPassword('demo1234')
    setError('')
  }

  return (
    <div className="w-full max-w-md space-y-8 rounded-3xl border border-slate-200/80 bg-white p-8 shadow-2xl shadow-slate-900/5 dark:border-slate-800 dark:bg-[#0c1926]">
      <div className="text-center">
        <h2 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Sign in to DocuScan AI
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Intelligent document processing &amp; layout analysis
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-2xl bg-rose-50 p-4 text-sm font-semibold text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Username
          </label>
          <div className="relative mt-1.5">
            <User size={17} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              required
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. demo"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Password
          </label>
          <div className="relative mt-1.5">
            <Lock size={17} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-teal-600 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
          <ArrowRight size={17} />
        </button>
      </form>

      {/* Divider */}
      <div className="relative my-2 text-center">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-200 dark:border-slate-800" />
        </div>
        <span className="relative bg-white px-3 text-xs font-semibold text-slate-400 dark:bg-[#0c1926]">
          OR
        </span>
      </div>

      <button
        type="button"
        onClick={fillDemo}
        className="flex w-full items-center justify-center gap-2 rounded-2xl border border-teal-200 bg-teal-50/50 py-2.5 text-xs font-bold text-teal-700 transition hover:bg-teal-100/60 dark:border-teal-900/50 dark:bg-teal-950/30 dark:text-teal-300"
      >
        <KeyRound size={15} />
        Fill demo credentials (demo / demo1234)
      </button>

      <p className="text-center text-xs font-medium text-slate-500">
        Don't have an account?{' '}
        <Link
          to={next && next !== '/dashboard' ? `/register?next=${encodeURIComponent(next)}` : '/register'}
          className="font-bold text-teal-600 hover:underline dark:text-teal-400"
        >
          Create an account
        </Link>
      </p>
    </div>
  )
}
