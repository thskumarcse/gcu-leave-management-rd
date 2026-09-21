import { useEffect, useMemo, useState } from 'react'
import Card from '../../components/common/Card'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import { fetchAdminEmployees, patchAdminEmployee } from '../../services/adminService'

export default function AdminEmployees() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  useEffect(() => {
    setPage(1)
  }, [query, status])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchAdminEmployees({ q: query, status, page })
        if (!cancelled) {
          setRows(body.data.results)
          setCount(body.data.count)
          setPageSize(body.data.page_size || 50)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load employees.')
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
  }, [query, status, page])

  async function updateRow(empId, payload) {
    setBusyId(empId)
    setError('')
    try {
      const body = await patchAdminEmployee(empId, payload)
      setRows((current) => current.map((row) => (row.emp_id === empId ? body.data : row)))
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not update that employee.')
    } finally {
      setBusyId('')
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const columns = useMemo(
    () => [
      { key: 'emp_id', header: 'Employee ID' },
      { key: 'name', header: 'Name' },
      { key: 'sub_department', header: 'Department' },
      { key: 'designation', header: 'Designation' },
      {
        key: 'status',
        header: 'Status',
        render: (row) => (
          <select
            value={row.status}
            disabled={busyId === row.emp_id}
            onChange={(event) => updateRow(row.emp_id, { status: event.target.value })}
            className="rounded-lg border border-ink-300 bg-paper-raised px-2 py-1 text-sm"
          >
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        ),
      },
    ],
    [busyId],
  )

  return (
    <>
      <div className="mb-6">
        <h2 className="font-display text-2xl font-semibold text-ink-950">Employees</h2>
        <p className="mt-1 text-sm text-ink-700">
          Activate or deactivate records. Grant admin or operator access from Settings → Access.
        </p>
      </div>
      <Card>
        <div className="mb-4 grid gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <TextField
              id="admin-employee-search"
              label="Search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, employee ID, department…"
            />
          </div>
          <label className="block" htmlFor="admin-employee-status">
            <span className="text-sm font-medium text-ink-800">Status</span>
            <select
              id="admin-employee-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm"
            >
              <option value="">All</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </label>
        </div>
        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading employees…
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
