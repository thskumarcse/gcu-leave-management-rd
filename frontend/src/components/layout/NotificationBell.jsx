import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/auth-context'
import { fetchNotifications, markNotificationRead } from '../../services/notificationService'
import { formatDateTime } from '../../utils/formatDate'

export default function NotificationBell() {
  const { user, patchUser } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const rootRef = useRef(null)
  const unread = user?.unread_notifications || 0

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const body = await fetchNotifications({ page: 1 })
        if (!cancelled) {
          setRows(body.data.results || [])
          patchUser({ unread_notifications: body.data.unread ?? unread })
        }
      } catch {
        if (!cancelled) setRows([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [open])

  useEffect(() => {
    function handleClick(event) {
      if (rootRef.current && !rootRef.current.contains(event.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  async function openItem(item) {
    if (!item.is_read) {
      try {
        const body = await markNotificationRead(item.id)
        patchUser({ unread_notifications: body.data.unread })
        setRows((current) =>
          current.map((row) => (row.id === item.id ? { ...row, is_read: true } : row)),
        )
      } catch {
        // Navigation still proceeds if the read call fails.
      }
    }
    setOpen(false)
    navigate(item.link || '/notifications')
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="relative rounded-lg border border-ink-200 bg-paper-raised px-3 py-1.5 text-sm text-ink-800"
        onClick={() => setOpen((current) => !current)}
        aria-label="Notifications"
      >
        Inbox
        {unread ? (
          <span className="ml-2 inline-flex min-w-5 items-center justify-center rounded-full bg-gold-400 px-1.5 text-[11px] font-semibold text-ink-950">
            {unread > 99 ? '99+' : unread}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-ink-200 bg-paper-raised shadow-lg">
          <div className="flex items-center justify-between border-b border-ink-100 px-3 py-2">
            <p className="text-sm font-medium text-ink-900">Notifications</p>
            <Link
              to="/notifications"
              className="text-xs font-medium text-ink-700 hover:underline"
              onClick={() => setOpen(false)}
            >
              View all
            </Link>
          </div>
          {loading ? (
            <p className="px-3 py-4 text-sm text-ink-600">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="px-3 py-4 text-sm text-ink-600">No notifications yet.</p>
          ) : (
            <ul className="max-h-80 overflow-y-auto">
              {rows.slice(0, 6).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`block w-full px-3 py-2.5 text-left hover:bg-ink-50 ${
                      item.is_read ? '' : 'bg-gold-100'
                    }`}
                    onClick={() => openItem(item)}
                  >
                    <p className="text-sm font-medium text-ink-950">{item.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-ink-600">{item.message}</p>
                    <p className="mt-1 text-[11px] text-ink-400">{formatDateTime(item.created_at)}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
