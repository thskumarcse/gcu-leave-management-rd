import { useEffect, useState } from 'react'
import AppShell from '../layouts/AppShell'
import Card from '../components/common/Card'
import Button from '../components/common/Button'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { useAuth } from '../context/auth-context'
import { fetchNotifications, markNotificationRead } from '../services/notificationService'
import { formatDateTime } from '../utils/formatDate'

export default function Notifications() {
  const { patchUser } = useAuth()
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchNotifications({ page })
        if (!cancelled) {
          setRows(body.data.results || [])
          setCount(body.data.count || 0)
          setPageSize(body.data.page_size || 20)
          patchUser({ unread_notifications: body.data.unread ?? 0 })
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load notifications.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [page])

  async function markAll() {
    try {
      const body = await markNotificationRead()
      patchUser({ unread_notifications: body.data.unread })
      setRows((current) => current.map((row) => ({ ...row, is_read: true })))
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not mark notifications read.')
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">Notifications</h2>
          <p className="mt-1 text-sm text-ink-700">
            Leave decisions and requests waiting on you appear here.
          </p>
        </div>
        <Button variant="secondary" onClick={markAll}>
          Mark all read
        </Button>
      </div>

      {error ? <p className="mb-4 text-sm text-danger-700">{error}</p> : null}

      <Card>
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading notifications…
          </div>
        ) : rows.length === 0 ? (
          <p className="text-sm text-ink-600">You have no notifications yet.</p>
        ) : (
          <ul className="divide-y divide-ink-100">
            {rows.map((item) => (
              <li key={item.id} className="py-3">
                <p className="text-sm font-medium text-ink-950">{item.title}</p>
                <p className="mt-1 text-sm text-ink-700">{item.message}</p>
                <p className="mt-1 text-xs text-ink-500">{formatDateTime(item.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {count > pageSize ? (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-ink-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((n) => n - 1)}>
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((n) => n + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </AppShell>
  )
}
