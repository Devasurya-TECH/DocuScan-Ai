import { useState } from 'react'
import Sidebar from './Sidebar'
import Navbar from './Navbar'

/**
 * Full authenticated layout: sidebar (desktop) + top navbar + page content.
 * Only renders for protected routes.
 */
export default function AppLayout({ children, theme, setTheme }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div
      className={`min-h-screen transition-colors duration-200 ${
        theme === 'dark'
          ? 'dark bg-[#07111a] text-slate-100'
          : 'bg-[#f8fafc] text-slate-900'
      }`}
    >
      <Sidebar open={sidebarOpen} close={() => setSidebarOpen(false)} />

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
        />
      )}

      <main className="min-h-screen lg:pl-[280px]">
        <Navbar
          theme={theme}
          setTheme={setTheme}
          onMenu={() => setSidebarOpen(true)}
        />

        <div className="mx-auto max-w-[1680px] px-4 py-6 sm:px-6 lg:px-9 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
