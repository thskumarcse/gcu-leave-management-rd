import { useEffect, useMemo, useState } from 'react'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import Table from '../../components/tables/Table'
import { fetchAdminAudit } from '../../services/adminService'
import { formatDateTime } from '../../utils/formatDate'
import { leaveStatusVariant, stepLabel } from '../../utils/leaveStatus'

export default function AdminAudit() {
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
        const body = await fetchAdminAudit({ page })
        if (!cancelled) {
          setRows(body.data.results)
          setCount(body.data.count)
          setPageSize(body.data.page_size || 20)
        }
      } catch (err) {
        if (!cancelled) setError(err?.response?.data?.message || 'Could not load the audit log.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [page])

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const columns = useMemo(
    () => [
      {
        key: 'created_at',
        header: 'When',
        render: (row) => formatDateTime(row.created_at),
      },
      {
        key: 'actor_name',
        header: 'Actor',
        render: (row) => `${row.actor_name} (${row.actor_emp_id})`,
      },
      {
        key: 'applicant_name',
        header: 'Applicant',
        render: (row) => `${row.applicant_name} (${row.applicant_emp_id})`,
      },
      { key: 'leave_type', header: 'Type' },
      {
        key: 'step',
        header: 'Step',
        render: (row) => stepLabel(row.step),
      },
      {
        key: 'decision',
        header: 'Decision',
        render: (row) => (
          <Badge variant={leaveStatusVariant(row.decision)} dot>
            {row.decision === 'APPROVED' ? 'Approved' : 'Rejected'}
          </Badge>
        ),
      },
      { key: 'remarks', header: 'Remarks' },
    ],
    [],
  )

  return (
    <>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Audit log</h2>
      <p className="mt-1 text-sm text-ink-700">Every approval and rejection, in order.</p>
      <Card className="mt-6">
        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading audit log…
          </div>
        ) : (
          <Table columns={columns} rows={rows} empty="No approval actions recorded yet." />
        )}
        {count > pageSize ? (
          <div className="mt-4 flex items-center justify-between border-t border-ink-100 pt-4">
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
      </Card>
    </>
  )
}
