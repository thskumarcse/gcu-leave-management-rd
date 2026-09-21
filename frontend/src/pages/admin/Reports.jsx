import { useEffect, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Card from '../../components/common/Card'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import StatCard from '../../components/dashboard/StatCard'
import TextField from '../../components/forms/TextField'
import { fetchAdminReport } from '../../services/adminService'

export default function AdminReports() {
  const [year, setYear] = useState(String(new Date().getFullYear()))
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchAdminReport({ year })
        if (!cancelled) setData(body.data)
      } catch (err) {
        if (!cancelled) setError(err?.response?.data?.message || 'Could not load the report.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [year])

  const statusRows = data
    ? Object.entries(data.by_status || {}).map(([status, count]) => ({ status, count }))
    : []

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">Reports</h2>
          <p className="mt-1 text-sm text-ink-700">Leave volume for the selected year.</p>
        </div>
        <div className="w-36">
          <TextField
            id="report-year"
            label="Year"
            type="number"
            value={year}
            onChange={(event) => setYear(event.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading report…
        </div>
      ) : null}
      {error ? <p className="mb-4 text-sm text-danger-700">{error}</p> : null}

      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Applications" value={data.total} />
            <StatCard label="Pending" value={data.by_status?.PENDING || 0} />
            <StatCard label="Approved" value={data.by_status?.APPROVED || 0} />
            <StatCard label="Rejected" value={data.by_status?.REJECTED || 0} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="font-display text-lg font-semibold text-ink-950">By status</h3>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={statusRows}>
                    <XAxis dataKey="status" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#1e3a5f" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card>
              <h3 className="font-display text-lg font-semibold text-ink-950">By leave type</h3>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.by_type || []}>
                    <XAxis dataKey="code" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#c9a227" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card className="mt-4">
            <h3 className="font-display text-lg font-semibold text-ink-950">Top departments</h3>
            <ul className="mt-4 divide-y divide-ink-100">
              {(data.by_department || []).map((row) => (
                <li key={row.department} className="flex justify-between py-2 text-sm">
                  <span className="text-ink-800">{row.department}</span>
                  <span className="font-medium text-ink-950">{row.count}</span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      ) : null}
    </>
  )
}
