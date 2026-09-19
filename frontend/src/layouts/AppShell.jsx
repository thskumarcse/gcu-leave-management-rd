import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import { useAuth } from '../context/auth-context'
import NotificationBell from '../components/layout/NotificationBell'

function navItems(user) {
  const items = [
    { to: '/', label: 'Dashboard', end: true },
    { to: '/leaves/apply', label: 'Apply leave' },
    { to: '/leaves', label: 'My leaves', end: true },
  ]
  if (user?.is_hod || user?.is_vc || user?.is_approver) {
    items.push({ to: '/approvals/dashboard', label: 'Approver home' })
    items.push({ to: '/approvals', label: 'Approvals', end: true })
  }
  if (user?.is_admin || user?.is_operator) {
    items.push({ to: '/employees', label: 'Directory' })
  }
  items.push({ to: '/profile', label: 'My profile' })
  if (user?.is_admin) {
    items.push({ to: '/settings', label: 'Settings' })
  }
  if (user?.is_admin || user?.is_operator) {
    items.push({ to: '/analytics', label: 'Analytics', end: true })
  }
  return items
}

const NAV_CLASS = ({ isActive }) =>
  `block rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-ink-800 text-gold-400'
      : 'text-ink-300 hover:bg-ink-900 hover:text-white'
  }`

export default function AppShell({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  const sidebar = (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-3 px-5 py-6">
        <img
          src={logo}
          alt="Girijananda Chowdhury University emblem"
          className="h-12 w-12 shrink-0 rounded-full object-cover"
        />
        <div>
          <p className="text-xs font-medium tracking-wide text-ink-300">GCU</p>
          <p className="font-display text-sm font-semibold leading-tight text-white">
            Leave Management
          </p>
        </div>
      </div>
      <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto px-3">
        {navItems(user).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={NAV_CLASS}
            onClick={() => setOpen(false)}
          >
            <span className="flex items-center justify-between gap-2">
              <span>{item.label}</span>
              {item.to === '/approvals' && user?.inbox_count ? (
                <span className="rounded-full bg-gold-400 px-2 py-0.5 text-[11px] font-semibold text-ink-950">
                  {user.inbox_count}
                </span>
              ) : null}
            </span>
          </NavLink>
        ))}
      </nav>
      <div className="shrink-0 border-t border-ink-800 px-5 py-4">
        <p className="truncate text-sm font-medium text-white">{user?.name}</p>
        <p className="truncate text-xs text-ink-400">{user?.emp_id}</p>
        <button
          type="button"
          onClick={handleSignOut}
          className="mt-3 text-sm text-ink-300 transition-colors hover:text-white"
        >
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-paper">
      {open ? (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-ink-950/40 lg:hidden"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex h-screen w-64 flex-col bg-ink-950 transition-transform lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebar}
      </aside>
      <div className="min-w-0 lg:pl-64">
        <header className="flex items-center justify-between border-b border-ink-200 bg-paper-raised px-4 py-3">
          <button
            type="button"
            className="rounded-lg border border-ink-200 px-3 py-1.5 text-sm text-ink-800 lg:hidden"
            onClick={() => setOpen(true)}
          >
            Menu
          </button>
          <p className="hidden text-sm text-ink-600 lg:block">Girijananda Chowdhury University</p>
          <div className="flex items-center gap-3">
            <span className="hidden truncate text-sm text-ink-700 sm:inline lg:hidden">{user?.name}</span>
            <NotificationBell />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
      </div>
    </div>
  )
}
