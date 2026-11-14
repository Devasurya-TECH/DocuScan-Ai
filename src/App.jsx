import { useEffect, useState } from 'react'
import { Route, Routes, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import NewScan from './pages/NewScan'
import WorkspaceDetail from './pages/WorkspaceDetail'
import { LanguageProvider } from './i18n'

function AppContent({ theme, setTheme }) {
  return (
    <AppShell theme={theme} setTheme={setTheme}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan" element={<NewScan />} />
        <Route path="/documents/:id" element={<WorkspaceDetail />} />
        <Route path="/documents/:id/workspace" element={<WorkspaceDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('docuscan-theme') || 'dark')

  useEffect(() => {
    const isDark = theme === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
    document.documentElement.setAttribute('data-theme', theme)
    document.body.className = isDark ? 'dark bg-[#07111a] text-slate-100' : 'bg-[#f8fafc] text-slate-900'
    localStorage.setItem('docuscan-theme', theme)
  }, [theme])

  return (
    <LanguageProvider>
      <AppContent theme={theme} setTheme={setTheme} />
    </LanguageProvider>
  )
}
