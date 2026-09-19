import { useEffect, useState } from 'react'
import AppShell from '../../layouts/AppShell'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextArea from '../../components/forms/TextArea'
import ApplicantLeaveSummary from './ApplicantLeaveSummary'
import { decideApproval, fetchApprovalInbox } from '../../services/approvalService'
import { formatDate } from '../../utils/formatDate'
import { formatLeaveDays, leaveStatusLabel, leaveStatusVariant, sessionLabel, stepLabel } from '../../utils/leaveStatus'
import { useAuth } from '../../context/auth-context'

export default function ApprovalsInbox() {
  const { user, refreshUser } = useAuth()
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [rejectingId, setRejectingId] = useState(null)
  const [remarks, setRemarks] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchApprovalInbox({ page })
        if (!cancelled) {
          setRows(body.data.results)
          setCount(body.data.count)
          setPageSize(body.data.page_size || 20)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load the approval inbox.')
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
  }, [page])

  async function submitDecision(id, decision, extra = {}) {
    setBusyId(id)
    setError('')
    try {
      await decideApproval(id, { decision, ...extra })
      setRows((current) => current.filter((row) => row.id !== id))
      setCount((current) => Math.max(0, current - 1))
      setRejectingId(null)
      setRemarks('')
      await refreshUser()
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not record that decision.')
    } finally {
      setBusyId(null)
    }
  }

  const roleLabel = user?.is_vc
    ? 'Vice-Chancellor'
    : user?.is_hod
      ? 'Head of Department'
      : 'Approver 1'
  const totalPages = Math.max(1, Math.ceil(count / pageSize))

  return (
    <AppShell>
      <div className="mb-6">
        <h2 className="font-display text-2xl font-semibold text-ink-950">Approvals</h2>
        <p className="mt-1 text-sm text-ink-700">
          Faculty leave waits on the HOD, then the Vice-Chancellor; HOD applicants go to the VC
          only. Staff leave waits on Approver 1, then Approver 2, then the VC. You are acting as{' '}
          {roleLabel}. Approve to send it on, or reject with a reason.
        </p>
      </div>

      {error ? <p className="mb-4 text-sm text-danger-700">{error}</p> : null}

      {loading ? (
        <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading inbox…
        </div>
      ) : rows.length === 0 ? (
        <Card>
          <p className="text-sm text-ink-600">Nothing is waiting for your decision.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {rows.map((row) => (
            <Card key={row.id}>
              <div>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-ink-950">
                      {row.employee?.name}{' '}
                      <span className="text-sm font-normal text-ink-500">{row.employee?.emp_id}</span>
                    </p>
                    <p className="mt-0.5 text-sm text-ink-600">
                      {row.employee?.designation}
                      {row.employee?.sub_department ? ` · ${row.employee.sub_department}` : ''}
                    </p>
                  </div>
                  <Badge variant={leaveStatusVariant(row.status)} dot>
                    {leaveStatusLabel(row.status, row.current_step)}
                  </Badge>
                </div>

                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink-500">Leave</dt>
                    <dd className="mt-0.5 text-ink-900">
                      {row.leave_type?.name}
                      {row.leave_type?.code === 'CL' && sessionLabel(row.session)
                        ? ` · ${sessionLabel(row.session)}`
                        : ''}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink-500">Dates</dt>
                    <dd className="mt-0.5 text-ink-900">
                      {formatDate(row.start_date)} – {formatDate(row.end_date)} (
                      {formatLeaveDays(row.days)})
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink-500">Step</dt>
                    <dd className="mt-0.5 text-ink-900">{stepLabel(row.current_step)}</dd>
                  </div>
                </dl>

                <p className="mt-4 text-sm text-ink-800">{row.reason}</p>

                {rejectingId === row.id ? (
                  <div className="mt-4 space-y-3">
                    <TextArea
                      id={`remarks-${row.id}`}
                      label="Reason for rejection"
                      value={remarks}
                      onChange={(event) => setRemarks(event.target.value)}
                      required
                      rows={3}
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        disabled={busyId === row.id || !remarks.trim()}
                        onClick={() =>
                          submitDecision(row.id, 'REJECTED', { remarks: remarks.trim() })
                        }
                      >
                        {busyId === row.id ? 'Rejecting…' : 'Confirm rejection'}
                      </Button>
                      <Button
                        variant="secondary"
                        disabled={busyId === row.id}
                        onClick={() => {
                          setRejectingId(null)
                          setRemarks('')
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      disabled={busyId === row.id}
                      onClick={() => submitDecision(row.id, 'APPROVED')}
                    >
                      {busyId === row.id ? 'Saving…' : 'Approve'}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busyId === row.id}
                      onClick={() => {
                        setRejectingId(row.id)
                        setRemarks('')
                      }}
                    >
                      Reject
                    </Button>
                  </div>
                )}
              </div>

              <div className="mt-6 border-t border-gold-100 pt-6">
                <ApplicantLeaveSummary
                  applicationId={row.id}
                  highlightCode={row.leave_type?.code}
                />
              </div>
            </Card>
          ))}
        </div>
      )}

      {count > pageSize ? (
        <div className="mt-4 flex items-center justify-between">
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
    </AppShell>
  )
}
