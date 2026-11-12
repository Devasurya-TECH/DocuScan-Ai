import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import Sidebar from './Sidebar'
import Navbar from './Navbar'

export default function AppShell({ children, theme, setTheme }) {
  const [open, setOpen] = useState(false)
  return <div className="min-h-screen bg-[#f7f8fc] text-slate-900 dark:bg-[#0c1220] dark:text-slate-100">
    <Sidebar open={open} close={() => setOpen(false)} />
    {open && <button aria-label="Close navigation" onClick={() => setOpen(false)} className="fixed inset-0 z-30 bg-slate-950/35 lg:hidden" />}
    <main className="min-h-screen lg:pl-72">
      <Navbar theme={theme} setTheme={setTheme} onMenu={() => setOpen(true)} />
      <button aria-label="Open navigation" onClick={() => setOpen(true)} className="fixed bottom-5 right-5 z-20 grid h-12 w-12 place-items-center rounded-2xl bg-slate-900 text-white shadow-xl lg:hidden"><Menu size={21} /></button>
      <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-9 lg:py-8">{children}</div>
    </main>
  </div>
}
