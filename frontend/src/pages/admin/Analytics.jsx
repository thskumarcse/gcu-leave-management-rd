import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../../layouts/AppShell'
import { useAuth } from '../../context/auth-context'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import Card from '../../components/common/Card'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import StatCard from '../../components/dashboard/StatCard'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import {
  exportAdminLeaves,
  fetchAdminEmployeeFilters,
  fetchAdminLeaves,
  fetchAdminOverview,
} from '../../services/adminService'
import { formatDateDMY, formatDateTime } from '../../utils/formatDate'
import { leaveStatusLabel, leaveStatusVariant, stepLabel } from '../../utils/leaveStatus'

const SELECT_CLASS =
  'mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'leaves', label: 'Leaves' },
]

const TAB_IDS = new Set(TABS.map((item) => item.id))

const LINKS = [
  { to: '/settings#view-roles', title: 'View approvers', text: 'See who is assigned as whose Approver 1 and Approver 2, plus HOD, VC, and Admin, and remove them.', adminOnly: true },
  { to: '/settings#assign-roles', title: 'Assign approvers', text: 'Select employees, then find their Approver 1 and Approver 2. Also assign HODs, the VC, and admin access.', adminOnly: true },
  { to: '/settings#change-password', title: 'Change password', text: 'Reset a forgotten password for any employee. They must change it after signing in.', adminOnly: true },
  { to: '/settings#leave-types', title: 'Leave type', text: 'Set yearly caps, who each type applies to, and active flags.', adminOnly: true },
  { to: '/admin/employees', title: 'Employees', text: 'Edit status, department, and admin access.', adminOnly: true },
  { to: '/admin/reports', title: 'Reports', text: 'Leave volume by status, type, and department.' },
  { to: '/admin/audit', title: 'Audit log', text: 'Every approval and rejection recorded in the system.' },
]

function tabFromHash() {
  const hash = window.location.hash.replace('#', '')
  if (TAB_IDS.has(hash)) return hash
  return 'overview'
}

export default function Analytics() {
  const { user } = useAuth()
  const [tab, setTab] = useState(() => tabFromHash())

  useEffect(() => {
    function onHash() {
      setTab(tabFromHash())
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  function selectTab(next) {
    setTab(next)
    const hash = next === 'overview' ? '' : `#${next}`
    const path = `/analytics${hash}`
    if (`${window.location.pathname}${window.location.hash}` !== path) {
      window.history.replaceState(null, '', path)
    }
  }

  return (
    <AppShell>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Analytics</h2>
      <p className="mt-1 text-sm text-ink-700">
        Overview stats and reports, plus a filterable list of leave applications.
        {user?.is_admin ? (
          <>
            {' '}
            <Link to="/settings" className="font-medium text-ink-800 hover:text-ink-950">
              Settings
            </Link>
            {' '}holds approver assignment and leave-type values.
          </>
        ) : null}
      </p>

      <div className="mt-6 flex flex-wrap gap-1 border-b border-ink-200" role="tablist" aria-label="Analytics">
        {TABS.map((item) => {
          const selected = tab === item.id
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`analytics-tab-${item.id}`}
              onClick={() => selectTab(item.id)}
              className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium ${
                selected
                  ? 'border-gold-500 text-ink-950'
                  : 'border-transparent text-ink-600 hover:text-ink-900'
              }`}
            >
              {item.label}
            </button>
          )
        })}
      </div>

      {tab === 'overview' ? <OverviewSection /> : null}
      {tab === 'leaves' ? <LeavesSection /> : null}
    </AppShell>
  )
}

function OverviewSection() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const visibleLinks = LINKS.filter((item) => !item.adminOnly || user?.is_admin)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const body = await fetchAdminOverview()
        if (!cancelled) setData(body.data)
      } catch (err) {
        if (!cancelled) setError(err?.response?.data?.message || 'Could not load admin overview.')
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
    <div>
      {loading ? (
        <div className="mt-8 flex items-center gap-2 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading overview…
        </div>
      ) : null}
      {error ? <p className="mt-6 text-sm text-danger-700">{error}</p> : null}

      {data ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard label="Employees" value={data.employees} hint={`${data.active_employees} active`} />
          <StatCard label="Pending leave" value={data.pending_leaves} />
          <StatCard label="Approved leave" value={data.approved_leaves} />
          <StatCard label="Leave types" value={data.leave_types} />
          <StatCard label="Approver assignments" value={data.approver_assignments} />
          <StatCard label="Admin accounts" value={data.admin_accounts} />
        </div>
      ) : null}

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {visibleLinks.map((item) => (
          <Link key={item.to} to={item.to}>
            <Card className="h-full transition-colors hover:border-ink-400">
              <h3 className="font-display text-lg font-semibold text-ink-950">{item.title}</h3>
              <p className="mt-1 text-sm text-ink-600">{item.text}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

function LeavesSection() {
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(20)
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [timelineRow, setTimelineRow] = useState(null)

  const filters = useMemo(
    () => ({ q: query, subDepartment: department, designation, start, end, page }),
    [query, department, designation, start, end, page],
  )

  useEffect(() => {
    setPage(1)
  }, [query, department, designation, start, end])

  useEffect(() => {
    let cancelled = false
    async function loadFilters() {
      try {
        const body = await fetchAdminEmployeeFilters(
          department ? { subDepartment: department } : {},
        )
        if (!cancelled) {
          setDepartments(body.data.departments || [])
          setDesignations(body.data.designations || [])
        }
      } catch {
        if (!cancelled) {
          setDepartments([])
          setDesignations([])
        }
      }
    }
    loadFilters()
    return () => {
      cancelled = true
    }
  }, [department])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchAdminLeaves(filters)
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
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [filters])

  async function handleExport() {
    setExporting(true)
    setError('')
    try {
      await exportAdminLeaves({
        q: query,
        subDepartment: department,
        designation,
        start,
        end,
      })
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not download the spreadsheet.')
    } finally {
      setExporting(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const columns = useMemo(
    () => [
      { key: 'serial_no', header: 'Serial No.' },
      { key: 'emp_id', header: 'Employee ID' },
      { key: 'name', header: 'Name' },
      { key: 'location', header: 'Location' },
      { key: 'leave_type', header: 'Leave Type' },
      {
        key: 'request_date',
        header: 'Request Date',
        render: (row) => formatDateDMY(row.request_date),
      },
      {
        key: 'from_date',
        header: 'From Date',
        render: (row) => formatDateDMY(row.from_date),
      },
      {
        key: 'to_date',
        header: 'To Date',
        render: (row) => formatDateDMY(row.to_date),
      },
      {
        key: 'status',
        header: 'Status',
        render: (row) => (
          <Badge variant={leaveStatusVariant(row.status)} dot>
            {row.status_label || leaveStatusLabel(row.status)}
          </Badge>
        ),
      },
      {
        key: 'timeline',
        header: 'Timeline',
        render: (row) => (
          <button
            type="button"
            className="font-medium text-ink-800 underline decoration-gold-400 underline-offset-2 hover:text-ink-950"
            onClick={() => setTimelineRow(row)}
          >
            View
          </button>
        ),
      },
      { key: 'total_days', header: 'Total Days' },
    ],
    [],
  )

  return (
    <div className="mt-6">
      <Card>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <TextField
            id="analytics-leaves-q"
            label="Name"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name or employee ID…"
          />
          <label className="block" htmlFor="analytics-leaves-dept">
            <span className="text-sm font-medium text-ink-800">Department</span>
            <select
              id="analytics-leaves-dept"
              value={department}
              onChange={(event) => {
                setDepartment(event.target.value)
                setDesignation('')
              }}
              className={SELECT_CLASS}
            >
              <option value="">All departments</option>
              {departments.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="block" htmlFor="analytics-leaves-desig">
            <span className="text-sm font-medium text-ink-800">Designation</span>
            <select
              id="analytics-leaves-desig"
              value={designation}
              onChange={(event) => setDesignation(event.target.value)}
              className={SELECT_CLASS}
            >
              <option value="">All designations</option>
              {designations.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <TextField
            id="analytics-leaves-from"
            label="From date"
            type="date"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
          <TextField
            id="analytics-leaves-to"
            label="To date"
            type="date"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
          <div className="flex items-end">
            <Button className="w-full" disabled={exporting || loading} onClick={handleExport}>
              {exporting ? 'Downloading…' : 'Download Excel'}
            </Button>
          </div>
        </div>

        {error ? <p className="mt-4 text-sm text-danger-700">{error}</p> : null}

        <div className="mt-6">
          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading leave applications…
            </div>
          ) : (
            <Table columns={columns} rows={rows} empty="No leave applications match those filters." />
          )}
        </div>

        {count > pageSize ? (
          <div className="mt-4 flex items-center justify-between border-t border-ink-100 pt-4">
            <p className="text-xs text-ink-500">
              {count} leave{count === 1 ? '' : 's'} · page {page} of {totalPages}
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
        ) : count ? (
          <p className="mt-4 text-xs text-ink-500">
            {count} leave{count === 1 ? '' : 's'}
          </p>
        ) : null}
      </Card>

      {timelineRow ? (
        <TimelineModal row={timelineRow} onClose={() => setTimelineRow(null)} />
      ) : null}
    </div>
  )
}

function TimelineModal({ row, onClose }) {
  const actions = row.actions || []

  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center px-4">
      <button
        type="button"
        className="absolute inset-0 bg-ink-950/40"
        aria-label="Close timeline"
        onClick={onClose}
      />
      <Card className="relative z-10 w-full max-w-lg">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-semibold text-ink-950">Approval timeline</h3>
            <p className="mt-1 text-sm text-ink-600">
              {row.name} ({row.emp_id}) · {row.leave_type}
            </p>
          </div>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
        {actions.length === 0 ? (
          <p className="mt-4 text-sm text-ink-600">No approval actions recorded yet.</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {actions.map((action) => (
              <li key={action.id || `${action.step}-${action.created_at}`} className="rounded-lg border border-ink-100 px-3 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-ink-950">
                    {action.step_label || stepLabel(action.step)}
                  </p>
                  <Badge variant={leaveStatusVariant(action.decision)} dot>
                    {action.decision_label || leaveStatusLabel(action.decision)}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-ink-600">
                  {action.actor_name}
                  {action.actor_emp_id ? ` (${action.actor_emp_id})` : ''}
                  {action.created_at ? ` · ${formatDateTime(action.created_at)}` : ''}
                </p>
                {action.remarks ? <p className="mt-1 text-sm text-ink-800">{action.remarks}</p> : null}
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  )
}
