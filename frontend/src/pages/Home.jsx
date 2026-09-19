import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../layouts/AppShell'
import Card from '../components/common/Card'
import Badge from '../components/common/Badge'
import Button from '../components/common/Button'
import LoadingSpinner from '../components/common/LoadingSpinner'
import StatCard from '../components/dashboard/StatCard'
import { useAuth } from '../context/auth-context'
import { fetchLeaveSummary } from '../services/leaveService'
import { formatDate } from '../utils/formatDate'
import { formatLeaveDays, leaveStatusLabel, leaveStatusVariant } from '../utils/leaveStatus'

export default function Home() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const body = await fetchLeaveSummary()
        if (!cancelled) setSummary(body.data)
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load your leave summary.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">
            Welcome, {user.name}
          </h2>
          <p className="mt-1 text-sm text-ink-700">
            {user.designation || user.group_name || 'Employee'}
            {user.department ? ` · ${user.department}` : ''}
          </p>
        </div>
        <Link to="/leaves/apply">
          <Button>Apply for leave</Button>
        </Link>
      </div>

      {loading ? (
        <div className="mt-8 flex items-center gap-2 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading dashboard…
        </div>
      ) : null}
      {error ? <p className="mt-6 text-sm text-danger-700">{error}</p> : null}

      {summary ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Pending" value={summary.pending} hint="Waiting for approval" />
            <StatCard label="Approved" value={summary.approved} />
            <StatCard label="Rejected" value={summary.rejected} />
            <StatCard label="Cancelled" value={summary.cancelled} />
          </div>

          {summary.balances?.length ? (
            <Card className="mt-4">
              <h3 className="font-display text-lg font-semibold text-ink-950">
                Leave balance this year
              </h3>
              <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {summary.balances.map((item) => (
                  <li key={item.code} className="rounded-lg border border-ink-100 px-3 py-2">
                    <p className="text-sm font-medium text-ink-950">{item.name}</p>
                    <p className="text-xs text-ink-600">
                      {item.max_days_per_year == null
                        ? `${item.used} day${item.used === 1 ? '' : 's'} used · no annual cap`
                        : `${item.remaining} of ${item.max_days_per_year} remaining (${item.used} used)`}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {user.is_hod || user.is_vc || user.is_approver ? (
            <Card className="mt-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-display text-lg font-semibold text-ink-950">
                    Waiting for your decision
                  </h3>
                  <p className="mt-1 text-sm text-ink-600">
                    {user.inbox_count
                      ? `${user.inbox_count} leave request${user.inbox_count === 1 ? '' : 's'} in your inbox.`
                      : 'Your approval inbox is empty.'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link to="/approvals/dashboard">
                    <Button variant="secondary">Approver dashboard</Button>
                  </Link>
                  <Link to="/approvals">
                    <Button>Open approvals</Button>
                  </Link>
                </div>
              </div>
            </Card>
          ) : null}

          {user.is_admin || user.is_operator ? (
            <Card className="mt-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 className="font-display text-lg font-semibold text-ink-950">
                    {user.is_admin ? 'Settings and analytics' : 'Analytics'}
                  </h3>
                  <p className="mt-1 text-sm text-ink-600">
                    {user.is_admin
                      ? 'Manage operators, leave types, and university-wide leave reports.'
                      : 'University-wide leave reports and application lists.'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {user.is_admin ? (
                    <Link to="/settings">
                      <Button variant="secondary">Open settings</Button>
                    </Link>
                  ) : null}
                  <Link to="/analytics">
                    <Button>Open analytics</Button>
                  </Link>
                </div>
              </div>
            </Card>
          ) : null}

          <Card className="mt-8">
            <div className="flex items-center justify-between gap-4">
              <h3 className="font-display text-lg font-semibold text-ink-950">Recent applications</h3>
              <Link to="/leaves" className="text-sm font-medium text-ink-800 hover:underline">
                View all →
              </Link>
            </div>
            {summary.recent.length === 0 ? (
              <p className="mt-4 text-sm text-ink-600">
                You have not applied for leave yet.
              </p>
            ) : (
              <ul className="mt-4 divide-y divide-ink-100">
                {summary.recent.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium text-ink-950">{item.leave_type.name}</p>
                      <p className="text-xs text-ink-600">
                        {formatDate(item.start_date)} – {formatDate(item.end_date)} ·{' '}
                        {formatLeaveDays(item.days)}
                      </p>
                    </div>
                    <Badge variant={leaveStatusVariant(item.status)} dot>
                      {leaveStatusLabel(item.status, item.current_step)}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      ) : null}
    </AppShell>
  )
}
