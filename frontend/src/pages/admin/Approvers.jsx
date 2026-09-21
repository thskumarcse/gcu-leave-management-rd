import { useEffect, useMemo, useState } from 'react'
import Card from '../../components/common/Card'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import { createAdminApprover, deleteAdminApprover, fetchAdminApprovers } from '../../services/adminService'

const EMPTY = { role: 'HOD', emp_id: '', department: '', sub_department: '' }

export default function AdminApprovers() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const body = await fetchAdminApprovers()
      setRows(body.data)
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not load approver assignments.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await createAdminApprover(form)
      setForm(EMPTY)
      await load()
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not save that assignment.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id) {
    setError('')
    try {
      await deleteAdminApprover(id)
      setRows((current) => current.filter((row) => row.id !== id))
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not remove that assignment.')
    }
  }

  const columns = useMemo(
    () => [
      { key: 'role', header: 'Role' },
      {
        key: 'employee',
        header: 'Employee',
        render: (row) => `${row.employee?.name || ''} (${row.employee?.emp_id || ''})`,
      },
      { key: 'sub_department', header: 'Department' },
      {
        key: 'actions',
        header: '',
        render: (row) => (
          <Button variant="secondary" onClick={() => remove(row.id)}>
            Remove
          </Button>
        ),
      },
    ],
    [],
  )

  return (
    <>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Approvers</h2>
      <p className="mt-1 text-sm text-ink-700">
        Faculty leave goes HOD → VC. HOD applicants go to the VC only. Staff leave goes
        Approver 1 → Approver 2 → VC when Approver 2 is assigned. Running{' '}
        <code className="rounded bg-ink-100 px-1">sync_approvers</code> fills HOD and Approver 1
        from designations; Approver 2 is assigned in Settings.
      </p>

      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Add or update assignment</h3>
        <form className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={handleCreate}>
          <label className="block" htmlFor="ap-role">
            <span className="text-sm font-medium text-ink-800">Role</span>
            <select
              id="ap-role"
              value={form.role}
              onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}
              className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm"
            >
              <option value="HOD">HOD</option>
              <option value="APPROVER_1">Approver 1</option>
              <option value="APPROVER_2">Approver 2</option>
              <option value="VC">Vice-Chancellor</option>
            </select>
          </label>
          <TextField
            id="ap-emp"
            label="Employee ID"
            value={form.emp_id}
            onChange={(event) => setForm((current) => ({ ...current, emp_id: event.target.value }))}
            required
          />
          <TextField
            id="ap-dept"
            label="School"
            value={form.department}
            onChange={(event) => setForm((current) => ({ ...current, department: event.target.value }))}
          />
          <TextField
            id="ap-sub"
            label="Department"
            value={form.sub_department}
            onChange={(event) => setForm((current) => ({ ...current, sub_department: event.target.value }))}
          />
          <div className="flex items-end">
            <Button type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4">
        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading assignments…
          </div>
        ) : (
          <Table columns={columns} rows={rows} empty="No approver assignments yet." />
        )}
      </Card>
    </>
  )
}
