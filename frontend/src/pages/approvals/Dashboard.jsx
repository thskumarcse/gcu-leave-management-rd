import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import StatCard from '../../components/dashboard/StatCard'
import { fetchApproverDashboard } from '../../services/dashboardService'
import { formatDate } from '../../utils/formatDate'
import { formatLeaveDays, leaveStatusLabel, leaveStatusVariant } from '../../utils/leaveStatus'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ApproverDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const body = await fetchApproverDashboard()
        if (!cancelled) setData(body.data)
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load the approver dashboard.')
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

  const role = data?.is_vc
    ? 'Vice-Chancellor'
    : data?.is_hod
      ? 'Head of Department'
      : 'Approver 1'

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">Approver dashboard</h2>
          <p className="mt-1 text-sm text-ink-700">
            {role} view of leave waiting on you, and decisions from the last 30 days.
          </p>
        </div>
        <Link to="/approvals">
          <Button>Open inbox</Button>
        </Link>
      </div>

      {loading ? (
        <div className="mt-8 flex items-center gap-2 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading dashboard…
        </div>
      ) : null}
      {error ? <p className="mt-6 text-sm text-danger-700">{error}</p> : null}

      {data ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Pending" value={data.pending} hint="Waiting on you now" />
            <StatCard label="Decided (30 days)" value={data.decided_last_30_days} />
            <StatCard label="Approved (30 days)" value={data.approved_last_30_days} />
            <StatCard label="Rejected (30 days)" value={data.rejected_last_30_days} />
          </div>

          {data.inbox_by_type?.length ? (
            <Card className="mt-4">
              <h3 className="font-display text-lg font-semibold text-ink-950">Pending by leave type</h3>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.inbox_by_type}>
                    <XAxis dataKey="code" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#1e3a5f" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          ) : null}

          <Card className="mt-4">
            <div className="flex items-center justify-between gap-4">
              <h3 className="font-display text-lg font-semibold text-ink-950">Recent queue</h3>
              <Link to="/approvals" className="text-sm font-medium text-ink-800 hover:underline">
                View all →
              </Link>
            </div>
            {data.recent?.length ? (
              <ul className="mt-4 divide-y divide-ink-100">
                {data.recent.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium text-ink-950">
                        {item.employee?.name} · {item.leave_type?.name}
                      </p>
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
            ) : (
              <p className="mt-4 text-sm text-ink-600">Nothing is waiting for your decision.</p>
            )}
          </Card>
        </>
      ) : null}
    </>
  )
}
