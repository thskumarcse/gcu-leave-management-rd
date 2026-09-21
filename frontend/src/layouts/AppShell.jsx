import { useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import logo from '../assets/logo.png'
import { useAuth } from '../context/auth-context'
import NotificationBell from '../components/layout/NotificationBell'
import NavIcon from '../components/layout/NavIcons'

function navItems(user) {
  const items = [
    { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
    { to: '/leaves/apply', label: 'Apply leave', icon: 'apply' },
    { to: '/leaves', label: 'My leaves', icon: 'leaves', end: true },
  ]
  if (user?.is_hod || user?.is_vc || user?.is_approver) {
    items.push({ to: '/approvals/dashboard', label: 'Approver home', icon: 'approver' })
    items.push({ to: '/approvals', label: 'Approvals', icon: 'approvals', end: true })
  }
  if (user?.is_admin || user?.is_operator) {
    items.push({ to: '/employees', label: 'Directory', icon: 'directory' })
  }
  items.push({ to: '/profile', label: 'My profile', icon: 'profile' })
  if (user?.is_admin) {
    items.push({ to: '/settings', label: 'Settings', icon: 'settings' })
  }
  if (user?.is_admin || user?.is_operator) {
    items.push({ to: '/analytics', label: 'Analytics', icon: 'analytics', end: true })
  }
  return items
}

const SIDEBAR_NAV_CLASS = ({ isActive }) =>
  `block rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-ink-800 text-gold-400'
      : 'text-ink-300 hover:bg-ink-900 hover:text-white'
  }`

function mobileNavClass({ isActive }) {
  return `relative flex min-h-[5.5rem] flex-col items-center justify-center gap-1.5 rounded-2xl border px-2 py-3 text-center shadow-sm transition-colors ${
    isActive
      ? 'border-ink-900 bg-ink-950 text-gold-400'
      : 'border-ink-200 bg-paper-raised text-ink-800 hover:border-ink-400'
  }`
}

function itemForPath(items, pathname) {
  const exact = items.find((item) => item.end && pathname === item.to)
  if (exact) return exact
  return [...items]
    .filter((item) => pathname === item.to || pathname.startsWith(`${item.to}/`))
    .sort((a, b) => b.to.length - a.to.length)[0]
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showMenu, setShowMenu] = useState(true)
  const items = navItems(user)
  const current = itemForPath(items, location.pathname)

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-paper">
      <aside className="fixed inset-y-0 left-0 z-30 hidden h-screen w-64 flex-col bg-ink-950 lg:flex">
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
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={SIDEBAR_NAV_CLASS}>
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
      </aside>

      <div className="min-w-0 lg:pl-64">
        <header className="flex items-center justify-between gap-3 border-b border-ink-200 bg-paper-raised px-4 py-3">
          <div className="flex min-w-0 items-center gap-3 lg:hidden">
            {showMenu ? (
              <img
                src={logo}
                alt="Girijananda Chowdhury University emblem"
                className="h-10 w-10 shrink-0 rounded-full object-cover"
              />
            ) : (
              <button
                type="button"
                onClick={() => setShowMenu(true)}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink-950 text-gold-400"
                aria-label="Back to menu"
              >
                <NavIcon name="home" className="h-5 w-5" />
              </button>
            )}
            <div className="min-w-0">
              <p className="font-display text-sm font-semibold leading-tight text-ink-950">
                {showMenu ? 'GCU Leave' : current?.label || 'GCU Leave'}
              </p>
              <p className="truncate text-xs text-ink-600">{user?.name}</p>
            </div>
          </div>
          <p className="hidden text-sm text-ink-600 lg:block">Girijananda Chowdhury University</p>
          <div className="flex shrink-0 items-center gap-2">
            <NotificationBell />
            <button
              type="button"
              onClick={handleSignOut}
              className="rounded-lg border border-ink-200 px-3 py-1.5 text-sm text-ink-800 lg:hidden"
            >
              Sign out
            </button>
          </div>
        </header>

        {showMenu ? (
          <nav
            className="grid grid-cols-2 gap-2.5 bg-ink-50 px-3 py-3 lg:hidden"
            aria-label="Main"
          >
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={mobileNavClass}
                onClick={() => setShowMenu(false)}
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                        isActive ? 'bg-ink-800 text-gold-400' : 'bg-gold-100 text-ink-900'
                      }`}
                    >
                      <NavIcon name={item.icon} className="h-6 w-6" />
                    </span>
                    <span className="text-[13px] font-semibold leading-tight">{item.label}</span>
                    {item.to === '/approvals' && user?.inbox_count ? (
                      <span className="absolute top-2 right-2 inline-flex min-w-5 items-center justify-center rounded-full bg-gold-400 px-1 text-[10px] font-semibold text-ink-950">
                        {user.inbox_count > 99 ? '99+' : user.inbox_count}
                      </span>
                    ) : null}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        ) : null}

        <main className={`mx-auto max-w-6xl px-4 py-8 sm:px-6 ${showMenu ? 'hidden lg:block' : ''}`}>
          {children}
        </main>
      </div>
    </div>
  )
}
