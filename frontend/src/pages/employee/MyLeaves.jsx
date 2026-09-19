import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../../layouts/AppShell'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import Table from '../../components/tables/Table'
import { cancelLeave, fetchLeaves } from '../../services/leaveService'
import { formatDate } from '../../utils/formatDate'
import { formatLeaveDays, leaveStatusLabel, leaveStatusVariant, sessionLabel } from '../../utils/leaveStatus'

export default function MyLeaves() {
  const [statusFilter, setStatusFilter] = useState('')
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cancellingId, setCancellingId] = useState(null)

  useEffect(() => {
    setPage(1)
  }, [statusFilter])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchLeaves({ status: statusFilter, page })
        if (!cancelled) {
          setRows(body.data.results)
          setCount(body.data.count)
          setPageSize(body.data.page_size || 20)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load leave applications.')
          setRows([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [statusFilter, page])

  async function handleCancel(id) {
    setCancellingId(id)
    try {
      await cancelLeave(id)
      setRows((current) =>
        current.map((row) => (row.id === id ? { ...row, status: 'CANCELLED' } : row)),
      )
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not cancel this application.')
    } finally {
      setCancellingId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))

  const columns = useMemo(
    () => [
      {
        key: 'leave_type',
        header: 'Type',
        render: (row) => {
          const part = row.leave_type?.code === 'CL' ? sessionLabel(row.session) : ''
          return part ? `${row.leave_type?.name} · ${part}` : row.leave_type?.name || '—'
        },
      },
      {
        key: 'applied',
        header: 'Applied on',
        render: (row) => formatDate(row.requested_on),
      },
      {
        key: 'dates',
        header: 'Dates',
        render: (row) => `${formatDate(row.start_date)} – ${formatDate(row.end_date)}`,
      },
      {
        key: 'days',
        header: 'Days',
        render: (row) => formatLeaveDays(row.days),
      },
      {
        key: 'source',
        header: '',
        render: (row) =>
          row.source === 'IMPORTED' ? <span className="text-xs text-ink-500">Record</span> : null,
      },
      {
        key: 'status',
        header: 'Status',
        render: (row) => (
          <Badge variant={leaveStatusVariant(row.status)} dot>
            {leaveStatusLabel(row.status, row.current_step)}
          </Badge>
        ),
      },
      {
        key: 'waiting_on',
        header: 'Waiting on',
        render: (row) =>
          row.status === 'PENDING' && row.waiting_on
            ? `${row.waiting_on.name}`
            : '—',
      },
      {
        key: 'actions',
        header: '',
        render: (row) =>
          row.status === 'PENDING' ? (
            <button
              type="button"
              className="text-sm font-medium text-danger-700 hover:underline disabled:opacity-50"
              disabled={cancellingId === row.id}
              onClick={() => handleCancel(row.id)}
            >
              {cancellingId === row.id ? 'Cancelling…' : 'Cancel'}
            </button>
          ) : null,
      },
    ],
    [cancellingId],
  )

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">My leaves</h2>
          <p className="mt-1 text-sm text-ink-700">
            Applications from this system and from the university leave report. Faculty
            requests wait with the HOD, then the Vice-Chancellor; HOD applicants go to the
            VC only. Pending requests can be cancelled until they are decided.
          </p>
        </div>
        <Link to="/leaves/apply">
          <Button>Apply for leave</Button>
        </Link>
      </div>

      <Card>
        <label className="mb-4 block max-w-xs" htmlFor="leave-status">
          <span className="text-sm font-medium text-ink-800">Status</span>
          <select
            id="leave-status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950 outline-none focus:border-ink-700"
          >
            <option value="">All</option>
            <option value="PENDING">Pending</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </label>

        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading applications…
          </div>
        ) : (
          <Table columns={columns} rows={rows} empty="No leave applications in this view." />
        )}

        {count > pageSize ? (
          <div className="mt-4 flex items-center justify-between border-t border-ink-100 pt-4">
            <p className="text-xs text-ink-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={page <= 1 || loading}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={page >= totalPages || loading}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        ) : null}
      </Card>
    </AppShell>
  )
}
