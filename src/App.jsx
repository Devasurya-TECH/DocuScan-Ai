import { useEffect, useState } from 'react'
import { Route, Routes, Navigate } from 'react-router-dom'

import { LanguageProvider } from './i18n'
import { AuthProvider } from './context/AuthContext'

import PrivateRoute from './components/PrivateRoute'
import AuthRoute from './components/AuthRoute'
import AppLayout from './components/AppLayout'
import AuthLayout from './components/AuthLayout'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import NewScan from './pages/NewScan'
import Documents from './pages/Documents'
import WorkspaceDetail from './pages/WorkspaceDetail'
import Settings from './pages/Settings'

function AppContent({ theme, setTheme }) {
  return (
    <Routes>
      {/* ── Public ── */}
      <Route path="/" element={<Landing />} />

      {/* ── Auth pages (no sidebar, no app nav) ── */}
      <Route
        path="/login"
        element={
          <AuthRoute>
            <AuthLayout>
              <Login />
            </AuthLayout>
          </AuthRoute>
        }
      />
      <Route
        path="/register"
        element={
          <AuthRoute>
            <AuthLayout>
              <Register />
            </AuthLayout>
          </AuthRoute>
        }
      />

      {/* ── Authenticated app pages (sidebar + navbar) ── */}
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <AppLayout theme={theme} setTheme={setTheme}>
              <Dashboard />
            </AppLayout>
          </PrivateRoute>
        }
      />
      <Route
        path="/scan"
        element={
          <PrivateRoute>
            <AppLayout theme={theme} setTheme={setTheme}>
              <NewScan />
            </AppLayout>
          </PrivateRoute>
        }
      />
      <Route
        path="/documents"
        element={
          <PrivateRoute>
            <AppLayout theme={theme} setTheme={setTheme}>
              <Documents />
            </AppLayout>
          </PrivateRoute>
        }
      />
      <Route
        path="/documents/:id"
        element={
          <PrivateRoute>
            <AppLayout theme={theme} setTheme={setTheme}>
              <WorkspaceDetail />
            </AppLayout>
          </PrivateRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <PrivateRoute>
            <AppLayout theme={theme} setTheme={setTheme}>
              <Settings theme={theme} setTheme={setTheme} />
            </AppLayout>
          </PrivateRoute>
        }
      />

      {/* ── Catch-all ── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem('docuscan-theme') || 'dark'
  )

  useEffect(() => {
    const isDark = theme === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
    document.documentElement.setAttribute('data-theme', theme)
    document.body.className = isDark
      ? 'dark bg-[#07111a] text-slate-100'
      : 'bg-[#f8fafc] text-slate-900'
    localStorage.setItem('docuscan-theme', theme)
  }, [theme])

  return (
    <LanguageProvider>
      <AuthProvider>
        <AppContent theme={theme} setTheme={setTheme} />
      </AuthProvider>
    </LanguageProvider>
  )
}
