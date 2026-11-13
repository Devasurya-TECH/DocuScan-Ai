import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import NewScan from './pages/NewScan'
import Documents from './pages/Documents'
import DocumentDetails from './pages/DocumentDetails'
import Settings from './pages/Settings'
import { LanguageProvider } from './i18n'

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('docuscan-theme') || 'light')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('docuscan-theme', theme)
  }, [theme])

  return <LanguageProvider><AppShell theme={theme} setTheme={setTheme}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/scan" element={<NewScan />} />
      <Route path="/documents" element={<Documents />} />
      <Route path="/documents/:id" element={<DocumentDetails />} />
      <Route path="/history" element={<Documents history />} />
      <Route path="/settings" element={<Settings theme={theme} setTheme={setTheme} />} />
      <Route path="*" element={<Dashboard />} />
    </Routes>
  </AppShell></LanguageProvider>
}
