import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import Sidebar from './Sidebar'
import Navbar from './Navbar'

export default function AppShell({ children, theme, setTheme }) {
  const [open, setOpen] = useState(false)
  const isDark = theme === 'dark'

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'dark bg-[#07111a] text-slate-100' : 'bg-[#f8fafc] text-slate-900'}`}>
      <Sidebar open={open} close={() => setOpen(false)} />
      {open && (
        <button
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-slate-950/35 lg:hidden"
        />
      )}
      <main className="min-h-screen lg:pl-[280px]">
        <Navbar theme={theme} setTheme={setTheme} onMenu={() => setOpen(true)} />
        <button
          aria-label="Open navigation"
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-20 grid h-12 w-12 place-items-center rounded-2xl bg-teal-600 text-white shadow-xl shadow-teal-600/30 lg:hidden"
        >
          <Menu size={21} />
        </button>
        <div className="mx-auto max-w-[1680px] px-4 py-6 sm:px-6 lg:px-9 lg:py-8">{children}</div>
      </main>
    </div>
  )
}
