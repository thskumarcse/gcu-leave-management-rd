import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import AppShell from '../../layouts/AppShell'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import { fetchEmployees } from '../../services/employeeService'
import { formatDate } from '../../utils/formatDate'

export default function Directory() {
  const [query, setQuery] = useState('')
  const [groupName, setGroupName] = useState('')
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setPage(1)
  }, [query, groupName])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchEmployees({ q: query, groupName, page })
        if (!cancelled) {
          setRows(body.data.results)
          setCount(body.data.count)
          setPageSize(body.data.page_size || 50)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load the employee directory.')
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
  }, [query, groupName, page])

  const totalPages = Math.max(1, Math.ceil(count / pageSize))

  const columns = useMemo(
    () => [
      {
        key: 'emp_id',
        header: 'Employee ID',
        render: (row) => (
          <Link to={`/employees/${row.emp_id}`} className="font-medium text-ink-900 hover:underline">
            {row.emp_id}
          </Link>
        ),
      },
      { key: 'name', header: 'Name' },
      { key: 'sub_department', header: 'Department' },
      { key: 'designation', header: 'Designation' },
      {
        key: 'group_name',
        header: 'Group',
        render: (row) => <Badge variant="neutral">{row.group_name || row.designation_type}</Badge>,
      },
      {
        key: 'joining_date',
        header: 'Joined',
        render: (row) => formatDate(row.joining_date),
      },
    ],
    [],
  )

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-semibold text-ink-950">Employee directory</h2>
          <p className="mt-1 text-sm text-ink-700">
            Master records imported from the university employee list. Date of birth and mobile
            numbers are not shown here.
          </p>
        </div>
        <p className="text-sm text-ink-500">{count} active employee{count === 1 ? '' : 's'}</p>
      </div>

      <Card>
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <TextField
              id="directory-search"
              label="Search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, employee ID, department…"
            />
          </div>
          <label className="block" htmlFor="group-name">
            <span className="text-sm font-medium text-ink-800">Group</span>
            <select
              id="group-name"
              value={groupName}
              onChange={(event) => setGroupName(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950 outline-none focus:border-ink-700"
            >
              <option value="">All</option>
              <option value="Faculty">Faculty</option>
              <option value="Admin">Admin</option>
              <option value="Other Employee">Other Employee</option>
            </select>
          </label>
        </div>

        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading directory…
          </div>
        ) : (
          <Table columns={columns} rows={rows} empty="No employees match those filters." />
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
