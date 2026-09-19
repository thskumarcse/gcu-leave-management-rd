import { useEffect, useMemo, useState } from 'react'
import AppShell from '../../layouts/AppShell'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import { createAdminLeaveType, fetchAdminLeaveTypes, patchAdminLeaveType } from '../../services/adminService'

const EMPTY = {
  name: '',
  code: '',
  applicable_to: 'ALL',
  max_days_per_year: '',
  sort_order: '10',
}

export default function AdminLeaveTypes() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const body = await fetchAdminLeaveTypes()
      setRows(body.data)
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not load leave types.')
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
      await createAdminLeaveType({
        ...form,
        code: form.code.trim().toUpperCase(),
        max_days_per_year: form.max_days_per_year ? Number(form.max_days_per_year) : null,
        sort_order: Number(form.sort_order || 0),
      })
      setForm(EMPTY)
      await load()
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not create that leave type.')
    } finally {
      setBusy(false)
    }
  }

  async function toggleActive(row) {
    try {
      const body = await patchAdminLeaveType(row.id, { is_active: !row.is_active })
      setRows((current) => current.map((item) => (item.id === row.id ? body.data : item)))
    } catch (err) {
      setError(err?.response?.data?.message || 'Could not update that leave type.')
    }
  }

  const columns = useMemo(
    () => [
      { key: 'code', header: 'Code' },
      { key: 'name', header: 'Name' },
      { key: 'applicable_to', header: 'Applies to' },
      {
        key: 'max_days_per_year',
        header: 'Cap',
        render: (row) => (row.max_days_per_year == null ? 'None' : row.max_days_per_year),
      },
      {
        key: 'is_active',
        header: 'Status',
        render: (row) => (
          <button type="button" onClick={() => toggleActive(row)}>
            <Badge variant={row.is_active ? 'success' : 'neutral'}>
              {row.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </button>
        ),
      },
    ],
    [],
  )

  return (
    <AppShell>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Leave types</h2>
      <p className="mt-1 text-sm text-ink-700">Catalogue used on the apply-leave form and imported history.</p>

      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Add leave type</h3>
        <form className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={handleCreate}>
          <TextField
            id="lt-name"
            label="Name"
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            required
          />
          <TextField
            id="lt-code"
            label="Code"
            value={form.code}
            onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
            required
          />
          <label className="block" htmlFor="lt-applies">
            <span className="text-sm font-medium text-ink-800">Applies to</span>
            <select
              id="lt-applies"
              value={form.applicable_to}
              onChange={(event) => setForm((current) => ({ ...current, applicable_to: event.target.value }))}
              className="mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm"
            >
              <option value="ALL">All</option>
              <option value="FACULTY">Faculty</option>
              <option value="STAFF">Staff</option>
            </select>
          </label>
          <TextField
            id="lt-cap"
            label="Yearly cap"
            type="number"
            value={form.max_days_per_year}
            onChange={(event) => setForm((current) => ({ ...current, max_days_per_year: event.target.value }))}
          />
          <div className="flex items-end">
            <Button type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Add'}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mt-4">
        {error ? <p className="mb-3 text-sm text-danger-700">{error}</p> : null}
        {loading ? (
          <div className="flex items-center gap-2 py-8 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading leave types…
          </div>
        ) : (
          <Table columns={columns} rows={rows} empty="No leave types yet." />
        )}
      </Card>
    </AppShell>
  )
}
