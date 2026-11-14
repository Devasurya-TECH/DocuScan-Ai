import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileScan, Lock, Mail, User, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const { register, login } = useAuth()
  const navigate = useNavigate()

  const handleChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.username.trim() || !formData.password) {
      setError('Username and password are required.')
      return
    }
    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await register(formData)
      setSuccess(true)
      // Auto-login
      setTimeout(async () => {
        try {
          await login(formData.username, formData.password)
          navigate('/documents')
        } catch {
          navigate('/login')
        }
      }, 1000)
    } catch (err) {
      const data = err.response?.data
      const detail = data?.username?.[0] || data?.password?.[0] || data?.email?.[0] || data?.detail || 'Registration failed.'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[85vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-slate-200/80 bg-white p-8 shadow-2xl shadow-slate-900/5 dark:border-slate-800 dark:bg-[#0c1926]">
        <div className="text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-teal-600 text-white shadow-xl shadow-teal-600/30">
            <FileScan size={28} />
          </div>
          <h2 className="mt-5 text-2xl font-extrabold tracking-tight">Create your account</h2>
          <p className="mt-2 text-sm text-slate-500">
            Start processing documents with DocuScan AI
          </p>
        </div>

        {error && (
          <div role="alert" className="flex items-start gap-3 rounded-2xl bg-rose-50 p-4 text-sm font-semibold text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-3 rounded-2xl bg-emerald-50 p-4 text-sm font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
            <CheckCircle2 size={18} className="shrink-0" />
            <span>Account created successfully! Signing in…</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Username
            </label>
            <div className="relative mt-1.5">
              <User size={18} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
              <input
                type="text"
                name="username"
                required
                value={formData.username}
                onChange={handleChange}
                placeholder="Choose a username"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Email (optional)
            </label>
            <div className="relative mt-1.5">
              <Mail size={18} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="name@example.com"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Password
            </label>
            <div className="relative mt-1.5">
              <Lock size={18} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
              <input
                type="password"
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                placeholder="At least 8 characters"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Confirm Password
            </label>
            <div className="relative mt-1.5">
              <Lock size={18} className="pointer-events-none absolute left-3.5 top-3 text-slate-400" />
              <input
                type="password"
                name="password_confirm"
                required
                value={formData.password_confirm}
                onChange={handleChange}
                placeholder="Repeat password"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm font-medium outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 dark:border-slate-700 dark:bg-slate-900 dark:focus:bg-slate-900"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-teal-600 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700 disabled:opacity-50"
          >
            {loading ? 'Creating account…' : 'Create account'}
            <ArrowRight size={17} />
          </button>
        </form>

        <p className="text-center text-xs font-medium text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="font-bold text-teal-600 hover:underline dark:text-teal-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
