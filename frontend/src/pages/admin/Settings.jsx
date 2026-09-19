import { useEffect, useMemo, useState } from 'react'
import AppShell from '../../layouts/AppShell'
import Badge from '../../components/common/Badge'
import Button from '../../components/common/Button'
import Card from '../../components/common/Card'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import EmployeeFinder from '../../components/forms/EmployeeFinder'
import TextField from '../../components/forms/TextField'
import Table from '../../components/tables/Table'
import { useAuth } from '../../context/auth-context'
import {
  assignEmployeeStaffApprovers,
  createAdminApprover,
  createAdminLeaveType,
  deleteAdminApprover,
  fetchAdminApprovers,
  fetchAdminEmployeeFilters,
  fetchAdminEmployees,
  fetchAdminLeaveTypes,
  fetchEmployeeApprovers,
  exportEmployeeApprovers,
  patchAdminAccess,
  patchAdminEmployee,
  createAdminEmployee,
  patchAdminLeaveType,
  patchEmployeeApprover,
  resetAdminEmployeePassword,
  deleteAdminEmployee,
  fetchAssignLeaveGrants,
  createAssignLeave,
} from '../../services/adminService'

const SELECT_CLASS =
  'mt-1.5 w-full rounded-lg border border-ink-300 bg-paper-raised px-3 py-2.5 text-sm text-ink-950'

const BLANK_FILTER = '__blank__'

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path d="M7.5 3.75A.75.75 0 018.25 3h3.5a.75.75 0 01.75.75V5h3.25a.75.75 0 010 1.5h-.66l-.47 8.48A2.25 2.25 0 0112.13 17.5H7.87a2.25 2.25 0 01-2.24-2.02L5.16 6.5H4.5a.75.75 0 010-1.5H7.5V3.75zM9 4.5v.5h2v-.5H9zM6.67 6.5l.46 8.32c.04.64.57 1.13 1.21 1.13h4.32c.64 0 1.17-.49 1.21-1.13L14.33 6.5H6.67z" />
    </svg>
  )
}

const EMPTY_ROLE = { role: 'HOD', emp_id: '', department: '', sub_department: '' }

const EMPTY_LEAVE = {
  name: '',
  code: '',
  applicable_to: 'ALL',
  max_days_per_year: '',
  sort_order: '10',
}

const ROLE_LABELS = {
  HOD: 'HOD',
  APPROVER_1: 'Approver 1',
  APPROVER_2: 'Approver 2',
  VC: 'Vice-Chancellor',
  ADMIN: 'Admin',
}

const ROLE_ORDER = {
  HOD: 0,
  APPROVER_1: 1,
  APPROVER_2: 2,
  VC: 3,
  ADMIN: 4,
}

const TABS = [
  { id: 'view-roles', label: 'View approvers' },
  { id: 'assign-roles', label: 'Assign approvers' },
  { id: 'employees', label: 'Employee' },
  { id: 'employee-approvers', label: 'Employee-Approver' },
  { id: 'assign-leave', label: 'Assign-Leave' },
  { id: 'change-password', label: 'Change password' },
  { id: 'leave-types', label: 'Leave type' },
  { id: 'access', label: 'Access', adminOnly: true },
]

const TAB_IDS = new Set(TABS.map((item) => item.id))

function fieldError(err, field) {
  const errors = err?.response?.data?.errors
  if (!errors) return ''
  const value = errors[field]
  if (Array.isArray(value)) return value[0]
  return typeof value === 'string' ? value : value?.[0] || ''
}

function apiMessage(err, fallback) {
  return err?.response?.data?.message || fallback
}

function personLabel(person) {
  if (!person) return '—'
  const name = person.name || ''
  const empId = person.emp_id || ''
  if (name && empId) return `${name} (${empId})`
  return name || empId || '—'
}

const HOD_IN_TITLE = /\bhod\b/i

function isHodTitle(row) {
  if (!row) return false
  if (row.is_hod_title) return true
  const designation = row.designation || row.employee?.designation || ''
  return HOD_IN_TITLE.test(designation)
}

function hodApproverLabel() {
  return 'Vice-Chancellor only'
}

const APPROVER_CHIP_CLASS =
  'inline-flex max-w-[16rem] cursor-pointer items-center rounded-lg border border-ink-200 bg-gold-100 px-2.5 py-1 text-left text-xs font-medium text-ink-800 transition-colors hover:bg-gold-200 disabled:cursor-not-allowed disabled:opacity-50'

function ApproverChip({ person, busy, disabled, onClick, slotLabel }) {
  if (!person) {
    return <span className="text-ink-400">—</span>
  }
  return (
    <button
      type="button"
      className={APPROVER_CHIP_CLASS}
      disabled={disabled}
      title={`Remove ${slotLabel} for this employee`}
      onClick={onClick}
    >
      {busy ? 'Removing…' : personLabel(person)}
    </button>
  )
}

function tabFromHash() {
  const hash = window.location.hash.replace('#', '')
  if (hash === 'roles' || hash === 'view-approvers') return 'view-roles'
  if (hash === 'assign' || hash === 'assign-role' || hash === 'assign-approvers') return 'assign-roles'
  if (hash === 'employee' || hash === 'employees') return 'employees'
  if (hash === 'employee-approver') return 'employee-approvers'
  if (hash === 'password') return 'change-password'
  if (hash === 'leave-type') return 'leave-types'
  if (hash === 'assignleave') return 'assign-leave'
  if (TAB_IDS.has(hash)) return hash
  return 'view-roles'
}

export default function Settings() {
  const { user } = useAuth()
  const [tab, setTab] = useState(() => tabFromHash())
  const visibleTabs = TABS.filter((item) => !item.adminOnly || user?.is_admin)

  useEffect(() => {
    function onHash() {
      setTab(tabFromHash())
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    if (tab === 'access' && !user?.is_admin) {
      setTab('view-roles')
      if (window.location.hash === '#access') {
        window.history.replaceState(null, '', '/settings#view-roles')
      }
    }
  }, [tab, user])

  function selectTab(next) {
    setTab(next)
    const hash = `#${next}`
    if (window.location.hash !== hash) {
      window.history.replaceState(null, '', `/settings${hash}`)
    }
  }

  return (
    <AppShell>
      <h2 className="font-display text-2xl font-semibold text-ink-950">Settings</h2>
      <p className="mt-1 text-sm text-ink-700">
        Review approver assignments, correct employee master records, set or remove personal Approver 1
        / Approver 2 mappings, credit or sanction leave, reset a forgotten password, or edit yearly
        leave-type values.
      </p>

      <div className="mt-6 flex flex-wrap gap-1 border-b border-ink-200" role="tablist" aria-label="Settings">
        {visibleTabs.map((item) => {
          const selected = tab === item.id
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`settings-tab-${item.id}`}
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

      {tab === 'view-roles' ? <ViewRolesSection /> : null}
      {tab === 'assign-roles' ? <AssignRolesSection /> : null}
      {tab === 'employees' ? <EmployeeMasterSection /> : null}
      {tab === 'employee-approvers' ? <EmployeeApproverSection /> : null}
      {tab === 'assign-leave' ? <AssignLeaveSection /> : null}
      {tab === 'change-password' ? <ResetPasswordSection /> : null}
      {tab === 'leave-types' ? <LeaveTypesSection /> : null}
      {tab === 'access' && user?.is_admin ? <AccessSection /> : null}
    </AppShell>
  )
}

function ViewRolesSection() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyKey, setBusyKey] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [assignmentsBody, adminsBody] = await Promise.all([
        fetchAdminApprovers(),
        fetchAdminEmployees({ isAdmin: true, page: 1, pageSize: 500 }),
      ])
      const assignments = (assignmentsBody.data || []).map((row) => ({
        ...row,
        kind: 'assignment',
        rowKey: `assignment-${row.id}`,
      }))
      const admins = (adminsBody.data?.results || []).map((employee) => ({
        kind: 'admin',
        role: 'ADMIN',
        emp_id: employee.emp_id,
        employee,
        department: employee.department || '',
        sub_department: employee.sub_department || '',
        rowKey: `admin-${employee.emp_id}`,
      }))
      const combined = [...assignments, ...admins].sort((a, b) => {
        const roleDiff = (ROLE_ORDER[a.role] ?? 99) - (ROLE_ORDER[b.role] ?? 99)
        if (roleDiff !== 0) return roleDiff
        const nameA = (a.employee?.name || '').toLowerCase()
        const nameB = (b.employee?.name || '').toLowerCase()
        return nameA.localeCompare(nameB)
      })
      setRows(combined)
    } catch (err) {
      setError(apiMessage(err, 'Could not load role assignments.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const adminCount = rows.filter((row) => row.kind === 'admin').length

  async function remove(row) {
    setError('')
    setNotice('')
    if (row.kind === 'admin') {
      const isSelf = user?.emp_id && row.emp_id?.toLowerCase() === user.emp_id.toLowerCase()
      if (adminCount <= 1) {
        setError(
          isSelf
            ? 'You cannot remove your own admin access while you are the only admin.'
            : 'Cannot remove the last remaining admin.',
        )
        return
      }
      setBusyKey(row.rowKey)
      try {
        await patchAdminAccess(row.emp_id, { is_admin: false })
        setRows((current) => current.filter((item) => item.rowKey !== row.rowKey))
        setNotice(`Removed admin access for ${row.employee?.name || row.emp_id}.`)
      } catch (err) {
        setError(apiMessage(err, 'Could not remove admin access.'))
      } finally {
        setBusyKey('')
      }
      return
    }

    setBusyKey(row.rowKey)
    try {
      await deleteAdminApprover(row.id)
      setRows((current) => current.filter((item) => item.rowKey !== row.rowKey))
      setNotice(`Removed ${ROLE_LABELS[row.role] || row.role} assignment.`)
    } catch (err) {
      setError(apiMessage(err, 'Could not remove that assignment.'))
    } finally {
      setBusyKey('')
    }
  }

  const columns = useMemo(
    () => [
      {
        key: 'role',
        header: 'Role',
        render: (row) => ROLE_LABELS[row.role] || row.role,
      },
      {
        key: 'employee',
        header: 'Employee',
        render: (row) => `${row.employee?.name || ''} (${row.employee?.emp_id || ''})`,
      },
      { key: 'sub_department', header: 'Department' },
      {
        key: 'actions',
        header: '',
        render: (row) => {
          const lastAdmin = row.kind === 'admin' && adminCount <= 1
          const canRemoveAdmin = Boolean(user?.is_admin)
          if (row.kind === 'admin' && !canRemoveAdmin) {
            return null
          }
          return (
            <Button
              variant="secondary"
              disabled={busyKey === row.rowKey || lastAdmin}
              title={
                lastAdmin
                  ? 'At least one admin must remain.'
                  : `Remove ${ROLE_LABELS[row.role] || row.role}`
              }
              onClick={() => remove(row)}
            >
              {busyKey === row.rowKey ? 'Removing…' : 'Remove'}
            </Button>
          )
        },
      },
    ],
    [adminCount, busyKey, user],
  )

  return (
    <section
      id="view-roles"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-view-roles"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">View approvers</h3>
        <p className="mt-1 text-sm text-ink-600">
          HOD, Vice-Chancellor, department Approver 1 / Approver 2 fallbacks, and Admin. Grant
          operator or admin access on the Access tab. Personal staff mappings are on the
          Employee-Approver tab.
        </p>
        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}
        <div className="mt-4">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading assignments…
            </div>
          ) : (
            <Table
              columns={columns}
              rows={rows}
              empty="No HOD, department Approver 1 / Approver 2, VC, or Admin assignments yet."
            />
          )}
        </div>
      </Card>
    </section>
  )
}

function AssignRolesSection() {
  const [form, setForm] = useState(EMPTY_ROLE)
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [peopleQuery, setPeopleQuery] = useState('')
  const [employees, setEmployees] = useState([])
  const [employeeCount, setEmployeeCount] = useState(0)
  const [selected, setSelected] = useState([])
  const [loadingPeople, setLoadingPeople] = useState(false)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [approver1, setApprover1] = useState(null)
  const [approver2, setApprover2] = useState(null)
  const [assigning, setAssigning] = useState(false)

  async function loadDepartmentOptions() {
    try {
      const body = await fetchAdminEmployeeFilters()
      setDepartments(body.data.departments || [])
    } catch {
      setDepartments([])
    }
  }

  useEffect(() => {
    loadDepartmentOptions()
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadDesignations() {
      try {
        const body = await fetchAdminEmployeeFilters({ department })
        if (!cancelled) {
          const next = body.data.designations || []
          setDesignations(next)
          setDesignation((current) => {
            if (!current || current === BLANK_FILTER) return current
            return next.includes(current) ? current : ''
          })
        }
      } catch {
        if (!cancelled) setDesignations([])
      }
    }
    loadDesignations()
    return () => {
      cancelled = true
    }
  }, [department])

  useEffect(() => {
    const term = peopleQuery.trim()
    const hasFilter = Boolean(department || designation || term)
    if (!hasFilter) {
      setEmployees([])
      setEmployeeCount(0)
      setSelected([])
      setLoadingPeople(false)
      return undefined
    }
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoadingPeople(true)
      try {
        const body = await fetchAdminEmployees({
          q: term || undefined,
          department,
          designation,
          status: 'Active',
          page: 1,
          pageSize: 500,
        })
        if (!cancelled) {
          setEmployees(body.data.results || [])
          setEmployeeCount(body.data.count || 0)
          setSelected([])
        }
      } catch (err) {
        if (!cancelled) {
          setEmployees([])
          setEmployeeCount(0)
          setError(apiMessage(err, 'Could not load employees.'))
        }
      } finally {
        if (!cancelled) setLoadingPeople(false)
      }
    }, term ? 200 : 0)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [department, designation, peopleQuery])

  useEffect(() => {
    const term = query.trim()
    if (!term) {
      setMatches([])
      setSearching(false)
      return undefined
    }
    let cancelled = false
    const handle = setTimeout(async () => {
      setSearching(true)
      try {
        const body = await fetchAdminEmployees({ q: term, page: 1 })
        if (!cancelled) setMatches(body.data.results || [])
      } catch {
        if (!cancelled) setMatches([])
      } finally {
        if (!cancelled) setSearching(false)
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [query])

  function pickEmployee(employee) {
    setForm((current) => ({
      ...current,
      emp_id: employee.emp_id,
      department: employee.department || current.department,
      sub_department: employee.sub_department || current.sub_department,
    }))
    setQuery(`${employee.name} (${employee.emp_id})`)
    setMatches([])
  }

  async function handleCreate(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await createAdminApprover(form)
      setForm(EMPTY_ROLE)
      setQuery('')
      setNotice('Role assignment saved.')
    } catch (err) {
      setError(apiMessage(err, 'Could not save that role assignment.'))
    } finally {
      setBusy(false)
    }
  }

  function toggleRow(empId) {
    setSelected((current) =>
      current.includes(empId) ? current.filter((id) => id !== empId) : [...current, empId],
    )
  }

  const allSelected = employees.length > 0 && employees.every((row) => selected.includes(row.emp_id))

  function toggleAll() {
    if (allSelected) {
      setSelected([])
      return
    }
    setSelected(employees.map((row) => row.emp_id))
  }

  async function assignPair() {
    const selectedStaff = selectedPeople.filter((row) => !isHodTitle(row))
    const selectedHods = selectedPeople.filter((row) => isHodTitle(row))
    const empIds = [...new Set(selectedStaff.map((row) => row.emp_id).filter(Boolean))]
    if (!empIds.length) {
      setError('')
      setNotice(
        'HOD leave is approved only by the Vice-Chancellor. Approver 1 and Approver 2 are not used.',
      )
      return
    }
    if (!approver1 || (approver2 && approver1.emp_id === approver2.emp_id)) {
      return
    }
    setAssigning(true)
    setError('')
    setNotice('')
    try {
      const body = await assignEmployeeStaffApprovers({
        emp_ids: empIds,
        approver1_emp_id: approver1.emp_id,
        approver2_emp_id: approver2?.emp_id || '',
      })
      const count = body.data?.count || empIds.length
      let message =
        body.message ||
        (approver2
          ? `Set Approver 1 and Approver 2 for ${count} selected employee${
              count === 1 ? '' : 's'
            }.`
          : `Set Approver 1 for ${count} selected employee${count === 1 ? '' : 's'}.`)
      if (selectedHods.length && !String(message).includes('HOD')) {
        message += ' HOD employees were skipped; they wait only on the Vice-Chancellor.'
      }
      setNotice(message)
      const assignedIds = new Set(
        (body.data?.emp_ids || empIds).map((id) => String(id).toLowerCase()),
      )
      const briefOf = (person) =>
        person
          ? {
              emp_id: person.emp_id,
              name: person.name,
              designation: person.designation,
              department: person.department,
              sub_department: person.sub_department,
              designation_type: person.designation_type,
            }
          : null
      const nextA1 = briefOf(approver1)
      const nextA2 = briefOf(approver2)
      setEmployees((current) =>
        current.map((row) =>
          assignedIds.has(String(row.emp_id).toLowerCase())
            ? { ...row, approver_1: nextA1, approver_2: nextA2 }
            : row,
        ),
      )
      const term = peopleQuery.trim()
      const refreshed = await fetchAdminEmployees({
        q: term || undefined,
        department,
        designation,
        status: 'Active',
        page: 1,
        pageSize: 500,
      })
      setEmployees(refreshed.data.results || [])
      setEmployeeCount(refreshed.data.count || 0)
    } catch (err) {
      setError(apiMessage(err, 'Could not assign Approver 1 and Approver 2.'))
    } finally {
      setAssigning(false)
    }
  }

  const selectedPeople = employees.filter((row) => selected.includes(row.emp_id))
  const selectedStaff = selectedPeople.filter((row) => !isHodTitle(row))
  const selectedHods = selectedPeople.filter((row) => isHodTitle(row))
  const hodOnlySelection = selectedPeople.length > 0 && selectedStaff.length === 0
  const hasPeopleFilter = Boolean(department || designation || peopleQuery.trim())

  const canAssign = hodOnlySelection
    ? !assigning
    : selectedStaff.length > 0 &&
      Boolean(approver1) &&
      (!approver2 || approver1.emp_id !== approver2.emp_id) &&
      !assigning

  const peopleColumns = useMemo(
    () => [
      {
        key: 'select',
        header: (
          <input
            type="checkbox"
            id="assign-select-all"
            checked={allSelected}
            onChange={toggleAll}
            aria-label="Select all matching employees"
          />
        ),
        render: (row) => (
          <input
            type="checkbox"
            name={`assign-select-${row.emp_id}`}
            checked={selected.includes(row.emp_id)}
            onChange={() => toggleRow(row.emp_id)}
            aria-label={`Select ${row.name}`}
          />
        ),
      },
      { key: 'emp_id', header: 'Employee ID' },
      { key: 'name', header: 'Name' },
      {
        key: 'designation',
        header: 'Designation',
        render: (row) => row.designation || '—',
      },
      {
        key: 'sub_department',
        header: 'Department',
        render: (row) => row.sub_department || '—',
      },
      {
        key: 'approver1',
        header: 'Approver 1',
        render: (row) => (isHodTitle(row) ? hodApproverLabel() : personLabel(row.approver_1)),
      },
      {
        key: 'approver2',
        header: 'Approver 2',
        render: (row) => (isHodTitle(row) ? '—' : personLabel(row.approver_2)),
      },
    ],
    [allSelected, selected, employees],
  )

  return (
    <section
      id="assign-roles"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-assign-roles"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Assign approvers</h3>
        <p className="mt-1 text-sm text-ink-600">
          Faculty leave goes HOD → VC. Staff leave goes Approver 1 → Approver 2 (if assigned) → VC.
          Approver 2 is optional for a personal mapping. If the designation contains HOD (for
          example Professor & HOD), leave goes only to the Vice-Chancellor — do not assign Approver
          1 or Approver 2 for that row.
        </p>

        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <TextField
            id="assign-filter-name"
            label="Search by name or ID"
            value={peopleQuery}
            onChange={(event) => setPeopleQuery(event.target.value)}
            placeholder="Name or employee ID…"
          />
          <label className="block" htmlFor="assign-filter-dept">
            <span className="text-sm font-medium text-ink-800">Department</span>
            <select
              id="assign-filter-dept"
              value={department}
              onChange={(event) => {
                setDepartment(event.target.value)
                setDesignation('')
              }}
              className={SELECT_CLASS}
            >
              <option value="">All departments</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {departments.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="block" htmlFor="assign-filter-desig">
            <span className="text-sm font-medium text-ink-800">Designation</span>
            <select
              id="assign-filter-desig"
              value={designation}
              onChange={(event) => setDesignation(event.target.value)}
              className={SELECT_CLASS}
            >
              <option value="">All designations</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {designations.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        {!hasPeopleFilter ? (
          <p className="mt-4 text-sm text-ink-600">
            Search by name or employee ID, or choose a department, to list employees.
          </p>
        ) : loadingPeople ? (
          <div className="mt-4 flex items-center gap-2 py-6 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading employees…
          </div>
        ) : (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-ink-900">Employees</h4>
            <p className="mt-1 text-sm text-ink-600">
              Select the people whose leave will be approved. They are not the Approver 1 / Approver
              2 list. Applies only to the selected employees.
            </p>
            <div className="mt-3">
              <Table
                columns={peopleColumns}
                rows={employees}
                empty="No active employees match those filters."
              />
            </div>
            {employeeCount > employees.length ? (
              <p className="mt-2 text-xs text-ink-500">
                Showing {employees.length} of {employeeCount}. Narrow the filters to see the rest.
              </p>
            ) : null}
          </div>
        )}

        {selected.length > 0 ? (
          <div className="mt-6 rounded-lg border border-ink-200 bg-paper px-4 py-4">
            <h4 className="text-sm font-semibold text-ink-900">Their approvers</h4>
            <p className="mt-1 text-sm text-ink-600">
              {selected.length} employee{selected.length === 1 ? '' : 's'} selected
              {selectedPeople.length
                ? `: ${selectedPeople
                    .slice(0, 6)
                    .map((row) => row.name)
                    .join(', ')}${selectedPeople.length > 6 ? '…' : ''}`
                : ''}
              .
              {hodOnlySelection
                ? ' Their designation contains HOD, so leave is approved only by the Vice-Chancellor.'
                : ' Find who will approve their leave — search the full directory, not only the rows above.'}
            </p>
            {selectedHods.length > 0 && selectedStaff.length > 0 ? (
              <p className="mt-2 text-sm text-ink-600">
                HOD rows ({selectedHods.map((row) => row.name).join(', ')}) stay on the
                Vice-Chancellor only. Approver 1 and Approver 2 apply to the other selected
                employees.
              </p>
            ) : null}
            {hodOnlySelection ? (
              <div className="mt-4">
                <Button type="button" disabled={!canAssign} onClick={assignPair}>
                  Use Vice-Chancellor only
                </Button>
              </div>
            ) : (
              <>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <EmployeeFinder
                    id="assign-approver-1"
                    label="Approver 1"
                    value={approver1}
                    onChange={setApprover1}
                    excludeId={approver2?.emp_id || ''}
                  />
                  <EmployeeFinder
                    id="assign-approver-2"
                    label="Approver 2 (optional)"
                    value={approver2}
                    onChange={setApprover2}
                    excludeId={approver1?.emp_id || ''}
                  />
                  <div className="flex items-end">
                    <Button type="button" disabled={!canAssign} onClick={assignPair}>
                      {assigning ? 'Saving…' : 'Set approvers'}
                    </Button>
                  </div>
                </div>
                <p className="mt-2 text-sm text-ink-600">
                  Applies only to the selected employees. Leave Approver 2 blank to use a single
                  personal approver; after Approver 1, leave goes to the Vice-Chancellor.
                </p>
                {approver1 && approver2 && approver1.emp_id === approver2.emp_id ? (
                  <p className="mt-2 text-sm text-danger-700">
                    Approver 1 and Approver 2 must be different people.
                  </p>
                ) : null}
              </>
            )}
          </div>
        ) : hasPeopleFilter && !loadingPeople ? (
          <p className="mt-3 text-sm text-ink-600">
            Select one or more employees in the table. HOD titles go to the Vice-Chancellor only;
            other staff need Approver 1. Approver 2 is optional.
          </p>
        ) : null}
      </Card>

      <details className="mt-6 rounded-xl border border-ink-200 bg-paper-raised px-5 py-4">
        <summary className="cursor-pointer font-display text-base font-semibold text-ink-950">
          HOD, Vice-Chancellor, and admin
        </summary>
        <p className="mt-2 text-sm text-ink-600">
          Assign a single HOD per unit or the Vice-Chancellor. Operator and admin access is granted
          on the Access tab.
        </p>

        <form className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={handleCreate}>
          <label className="block" htmlFor="assign-role">
            <span className="text-sm font-medium text-ink-800">Role</span>
            <select
              id="assign-role"
              value={form.role}
              onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}
              className={SELECT_CLASS}
            >
              <option value="HOD">HOD</option>
              <option value="VC">Vice-Chancellor</option>
            </select>
          </label>
          <TextField
            id="assign-emp"
            label="Employee ID"
            value={form.emp_id}
            onChange={(event) => setForm((current) => ({ ...current, emp_id: event.target.value }))}
            required
          />
          <TextField
            id="assign-dept"
            label="School"
            value={form.department}
            onChange={(event) =>
              setForm((current) => ({ ...current, department: event.target.value }))
            }
          />
          <TextField
            id="assign-sub"
            label="Department"
            value={form.sub_department}
            onChange={(event) =>
              setForm((current) => ({ ...current, sub_department: event.target.value }))
            }
          />
          <div className="flex items-end">
            <Button type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Assign role'}
            </Button>
          </div>
        </form>

        <div className="relative mt-4">
          <TextField
            id="assign-employee-search"
            label="Search employees (fills the form)"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name or employee ID…"
          />
          {searching ? <p className="mt-2 text-xs text-ink-500">Searching…</p> : null}
          {matches.length ? (
            <ul className="mt-2 divide-y divide-ink-100 overflow-hidden rounded-lg border border-ink-200">
              {matches.slice(0, 8).map((employee) => (
                <li key={employee.emp_id} className="bg-paper-raised">
                  <button
                    type="button"
                    className="w-full px-3 py-2.5 text-left hover:bg-ink-50"
                    onClick={() => pickEmployee(employee)}
                  >
                    <p className="truncate text-sm font-medium text-ink-950">
                      {employee.name}{' '}
                      <span className="font-normal text-ink-500">({employee.emp_id})</span>
                    </p>
                    <p className="truncate text-xs text-ink-500">
                      {employee.sub_department || employee.department || 'No department'}
                      {employee.designation ? ` · ${employee.designation}` : ''}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </details>
    </section>
  )
}

function AssignLeaveSection() {
  const [employee, setEmployee] = useState(null)
  const [leaveTypes, setLeaveTypes] = useState([])
  const [leaveTypeId, setLeaveTypeId] = useState('')
  const [days, setDays] = useState('')
  const [action, setAction] = useState('CREDIT')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [year, setYear] = useState(String(new Date().getFullYear()))
  const [reason, setReason] = useState('')
  const [grants, setGrants] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  async function loadGrants() {
    setLoading(true)
    try {
      const [typesBody, grantsBody] = await Promise.all([
        fetchAdminLeaveTypes(),
        fetchAssignLeaveGrants(),
      ])
      const types = (typesBody.data || []).filter((item) => item.is_active !== false)
      setLeaveTypes(types)
      setLeaveTypeId((current) => current || (types[0] ? String(types[0].id) : ''))
      setGrants(grantsBody.data || [])
    } catch (err) {
      setError(apiMessage(err, 'Could not load Assign-Leave.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGrants()
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!employee?.emp_id) {
      setFieldErrors({ emp_id: 'Select an employee.' })
      return
    }
    setSaving(true)
    setError('')
    setNotice('')
    setFieldErrors({})
    try {
      const body = await createAssignLeave({
        emp_id: employee.emp_id,
        leave_type_id: Number(leaveTypeId),
        days: Number(days),
        action,
        start_date: action === 'SANCTION' ? startDate || undefined : undefined,
        end_date: action === 'SANCTION' && endDate ? endDate : undefined,
        year: action === 'CREDIT' ? Number(year) : undefined,
        reason: reason.trim(),
      })
      setNotice(body.message || 'Leave assigned.')
      setDays('')
      setReason('')
      setStartDate('')
      setEndDate('')
      await loadGrants()
    } catch (err) {
      setError(apiMessage(err, 'Could not assign leave.'))
      setFieldErrors({
        emp_id: fieldError(err, 'emp_id'),
        leave_type_id: fieldError(err, 'leave_type_id'),
        days: fieldError(err, 'days'),
        start_date: fieldError(err, 'start_date'),
        end_date: fieldError(err, 'end_date'),
        year: fieldError(err, 'year'),
        reason: fieldError(err, 'reason'),
      })
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo(
    () => [
      {
        key: 'kind',
        header: 'Action',
        render: (row) => (row.kind === 'CREDIT' ? 'Credit' : 'Sanctioned'),
      },
      {
        key: 'employee',
        header: 'Employee',
        render: (row) => `${row.name || ''} (${row.emp_id || ''})`,
      },
      {
        key: 'leave_type',
        header: 'Leave type',
        render: (row) => row.leave_type_code || row.leave_type,
      },
      { key: 'days', header: 'Days' },
      {
        key: 'when',
        header: 'Period / year',
        render: (row) =>
          row.kind === 'CREDIT'
            ? String(row.year || '')
            : [row.start_date, row.end_date].filter(Boolean).join(' → '),
      },
      {
        key: 'reason',
        header: 'Reason',
        render: (row) => row.reason || '—',
      },
    ],
    [],
  )

  return (
    <section
      id="assign-leave"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-assign-leave"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Assign-Leave</h3>
        <p className="mt-1 text-sm text-ink-600">
          Credit extra days onto a person&apos;s yearly balance, or sanction approved leave that
          skips Approver 1 / Approver 2 / VC and counts as used.
        </p>
        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}

        <form className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={handleSubmit}>
          <div className="sm:col-span-2 lg:col-span-3">
            <EmployeeFinder
              id="assign-leave-employee"
              label="Employee"
              value={employee}
              onChange={setEmployee}
            />
            {fieldErrors.emp_id ? (
              <p className="mt-1 text-xs text-danger-700">{fieldErrors.emp_id}</p>
            ) : null}
          </div>
          <label className="block" htmlFor="assign-leave-type">
            <span className="text-sm font-medium text-ink-800">Leave type</span>
            <select
              id="assign-leave-type"
              value={leaveTypeId}
              onChange={(event) => setLeaveTypeId(event.target.value)}
              className={SELECT_CLASS}
              required
            >
              {leaveTypes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.code} — {item.name}
                </option>
              ))}
            </select>
            {fieldErrors.leave_type_id ? (
              <p className="mt-1 text-xs text-danger-700">{fieldErrors.leave_type_id}</p>
            ) : null}
          </label>
          <TextField
            id="assign-leave-days"
            label="Days"
            type="number"
            step="0.5"
            min="0.5"
            value={days}
            onChange={(event) => setDays(event.target.value)}
            required
            error={fieldErrors.days}
          />
          <label className="block" htmlFor="assign-leave-action">
            <span className="text-sm font-medium text-ink-800">Action</span>
            <select
              id="assign-leave-action"
              value={action}
              onChange={(event) => setAction(event.target.value)}
              className={SELECT_CLASS}
            >
              <option value="CREDIT">Credit balance</option>
              <option value="SANCTION">Sanction approved leave</option>
            </select>
          </label>
          {action === 'CREDIT' ? (
            <TextField
              id="assign-leave-year"
              label="Year"
              type="number"
              value={year}
              onChange={(event) => setYear(event.target.value)}
              error={fieldErrors.year}
            />
          ) : (
            <>
              <TextField
                id="assign-leave-start"
                label="Start date"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
                required
                error={fieldErrors.start_date}
              />
              <TextField
                id="assign-leave-end"
                label="End date (optional)"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
                error={fieldErrors.end_date}
              />
            </>
          )}
          <div className="sm:col-span-2 lg:col-span-3">
            <TextField
              id="assign-leave-reason"
              label="Reason (optional)"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              error={fieldErrors.reason}
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : action === 'CREDIT' ? 'Credit days' : 'Sanction leave'}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Recent grants</h3>
        {loading ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading…
          </div>
        ) : (
          <div className="mt-4">
            <Table columns={columns} rows={grants} empty="No credited or sanctioned leave yet." />
          </div>
        )}
      </Card>
    </section>
  )
}

function AccessSection() {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyKey, setBusyKey] = useState('')

  useEffect(() => {
    async function loadDepartments() {
      try {
        const body = await fetchAdminEmployeeFilters()
        setDepartments(body.data.departments || [])
      } catch {
        setDepartments([])
      }
    }
    loadDepartments()
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadDesignations() {
      try {
        const body = await fetchAdminEmployeeFilters({ department })
        if (!cancelled) {
          const next = body.data.designations || []
          setDesignations(next)
          setDesignation((current) => {
            if (!current || current === BLANK_FILTER) return current
            return next.includes(current) ? current : ''
          })
        }
      } catch {
        if (!cancelled) setDesignations([])
      }
    }
    loadDesignations()
    return () => {
      cancelled = true
    }
  }, [department])

  useEffect(() => {
    setPage(1)
  }, [query, department, designation])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchAdminEmployees({
          q: query.trim() || undefined,
          department,
          designation,
          page,
        })
        if (!cancelled) {
          setRows(body.data.results || [])
          setCount(body.data.count || 0)
          setPageSize(body.data.page_size || 50)
        }
      } catch (err) {
        if (!cancelled) {
          setError(apiMessage(err, 'Could not load employees.'))
          setRows([])
          setCount(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, query.trim() ? 200 : 0)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [query, department, designation, page])

  const adminCount = rows.filter((row) => row.is_admin).length
  const totalAdminsUnknown = page > 1 || count > rows.length

  async function toggleFlag(row, field, value) {
    const isSelf = user?.emp_id && row.emp_id?.toLowerCase() === user.emp_id.toLowerCase()
    if (field === 'is_admin' && !value && row.is_admin && !totalAdminsUnknown && adminCount <= 1) {
      setError(
        isSelf
          ? 'You cannot remove your own admin access while you are the only admin on this page.'
          : 'Cannot remove the last remaining admin.',
      )
      return
    }
    setBusyKey(`${row.emp_id}-${field}`)
    setError('')
    setNotice('')
    try {
      const body = await patchAdminAccess(row.emp_id, { [field]: value })
      setRows((current) =>
        current.map((item) => (item.emp_id === row.emp_id ? { ...item, ...body.data } : item)),
      )
      const label = field === 'is_admin' ? 'Admin' : 'Operator'
      setNotice(
        value
          ? `Granted ${label} access to ${body.data?.name || row.emp_id}.`
          : `Removed ${label} access from ${body.data?.name || row.emp_id}.`,
      )
    } catch (err) {
      setError(apiMessage(err, 'Could not update access.'))
    } finally {
      setBusyKey('')
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const columns = useMemo(
    () => [
      { key: 'emp_id', header: 'Employee ID' },
      { key: 'name', header: 'Name' },
      {
        key: 'sub_department',
        header: 'Department',
        render: (row) => row.sub_department || '—',
      },
      {
        key: 'designation',
        header: 'Designation',
        render: (row) => row.designation || '—',
      },
      {
        key: 'is_operator',
        header: 'Operator',
        render: (row) => (
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(row.is_operator)}
              disabled={busyKey === `${row.emp_id}-is_operator`}
              onChange={(event) => toggleFlag(row, 'is_operator', event.target.checked)}
            />
            {row.is_operator ? <Badge variant="gold">Operator</Badge> : <span className="text-ink-500">No</span>}
          </label>
        ),
      },
      {
        key: 'is_admin',
        header: 'Admin',
        render: (row) => (
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(row.is_admin)}
              disabled={busyKey === `${row.emp_id}-is_admin`}
              onChange={(event) => toggleFlag(row, 'is_admin', event.target.checked)}
            />
            {row.is_admin ? <Badge variant="gold">Admin</Badge> : <span className="text-ink-500">No</span>}
          </label>
        ),
      },
    ],
    [busyKey, adminCount, totalAdminsUnknown, user],
  )

  return (
    <section
      id="access"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-access"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Access</h3>
        <p className="mt-1 text-sm text-ink-600">
          Operators can use Analytics only. Admins can also grant or revoke operator and
          admin access. Faculty, staff, and approvers are not assigned here.
        </p>
        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <TextField
            id="access-filter-name"
            label="Name"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name or employee ID…"
          />
          <label className="block" htmlFor="access-filter-dept">
            <span className="text-sm font-medium text-ink-800">Department</span>
            <select
              id="access-filter-dept"
              value={department}
              onChange={(event) => {
                setDepartment(event.target.value)
                setDesignation('')
              }}
              className={SELECT_CLASS}
            >
              <option value="">All departments</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {departments.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="block" htmlFor="access-filter-desig">
            <span className="text-sm font-medium text-ink-800">Designation</span>
            <select
              id="access-filter-desig"
              value={designation}
              onChange={(event) => setDesignation(event.target.value)}
              className={SELECT_CLASS}
            >
              <option value="">All designations</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {designations.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading employees…
            </div>
          ) : (
            <Table columns={columns} rows={rows} empty="No employees match these filters." />
          )}
        </div>
        {totalPages > 1 ? (
          <div className="mt-4 flex items-center justify-between text-sm text-ink-600">
            <span>
              {count} employee{count === 1 ? '' : 's'}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </Button>
              <span className="self-center">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        ) : null}
      </Card>
    </section>
  )
}

const EMPTY_EMPLOYEE_EDIT = {
  name: '',
  email: '',
  sub_department: '',
  designation: '',
  designation_type: 'STAFF',
  status: 'Active',
}

const EMPTY_EMPLOYEE_ADD = {
  emp_id: '',
  name: '',
  designation: '',
  sub_department: '',
}

function EmployeeMasterSection() {
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState(EMPTY_EMPLOYEE_EDIT)
  const [addForm, setAddForm] = useState(EMPTY_EMPLOYEE_ADD)
  const [fieldErrors, setFieldErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [confirmingId, setConfirmingId] = useState('')
  const [deletingId, setDeletingId] = useState('')

  useEffect(() => {
    async function loadDepartments() {
      try {
        const body = await fetchAdminEmployeeFilters()
        setDepartments(body.data.departments || [])
      } catch {
        setDepartments([])
      }
    }
    loadDepartments()
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadDesignations() {
      try {
        const body = await fetchAdminEmployeeFilters({ department })
        if (!cancelled) {
          const next = body.data.designations || []
          setDesignations(next)
          setDesignation((current) => {
            if (!current || current === BLANK_FILTER) return current
            return next.includes(current) ? current : ''
          })
        }
      } catch {
        if (!cancelled) setDesignations([])
      }
    }
    loadDesignations()
    return () => {
      cancelled = true
    }
  }, [department])

  useEffect(() => {
    setPage(1)
  }, [query, department, designation])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchAdminEmployees({
          q: query.trim() || undefined,
          department,
          designation,
          page,
        })
        if (!cancelled) {
          setRows(body.data.results || [])
          setCount(body.data.count || 0)
          setPageSize(body.data.page_size || 50)
        }
      } catch (err) {
        if (!cancelled) {
          setError(apiMessage(err, 'Could not load employees.'))
          setRows([])
          setCount(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, query.trim() ? 200 : 0)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [query, department, designation, page])

  function startEdit(row) {
    setConfirmingId('')
    setAdding(false)
    setAddForm(EMPTY_EMPLOYEE_ADD)
    setEditing(row)
    setForm({
      name: row.name || '',
      email: row.email || '',
      sub_department: row.sub_department || '',
      designation: row.designation || '',
      designation_type: row.designation_type || 'STAFF',
      status: row.status || 'Active',
    })
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  function cancelEdit() {
    setEditing(null)
    setAdding(false)
    setForm(EMPTY_EMPLOYEE_EDIT)
    setAddForm(EMPTY_EMPLOYEE_ADD)
    setFieldErrors({})
  }

  function startAdd() {
    setConfirmingId('')
    setEditing(null)
    setForm(EMPTY_EMPLOYEE_EDIT)
    setAdding(true)
    setAddForm(EMPTY_EMPLOYEE_ADD)
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  async function handleAdd(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    setFieldErrors({})
    try {
      const body = await createAdminEmployee({
        emp_id: addForm.emp_id.trim(),
        name: addForm.name.trim(),
        designation: addForm.designation.trim(),
        department: addForm.sub_department.trim(),
      })
      setRows((current) => [body.data, ...current.filter((row) => row.emp_id !== body.data.emp_id)])
      setCount((current) => current + 1)
      if (body.data?.sub_department && !departments.includes(body.data.sub_department)) {
        setDepartments((current) => [...current, body.data.sub_department].sort())
      }
      setNotice(body.message || `Added ${body.data?.name || body.data?.emp_id}.`)
      setAdding(false)
      setAddForm(EMPTY_EMPLOYEE_ADD)
    } catch (err) {
      setError(apiMessage(err, 'Could not add that employee.'))
      setFieldErrors({
        emp_id: fieldError(err, 'emp_id'),
        name: fieldError(err, 'name'),
        designation: fieldError(err, 'designation'),
        sub_department: fieldError(err, 'department') || fieldError(err, 'sub_department'),
      })
    } finally {
      setSaving(false)
    }
  }

  async function handleSave(event) {
    event.preventDefault()
    if (!editing?.emp_id) return
    setSaving(true)
    setError('')
    setNotice('')
    setFieldErrors({})
    try {
      const body = await patchAdminEmployee(editing.emp_id, {
        name: form.name.trim(),
        email: form.email.trim(),
        sub_department: form.sub_department.trim(),
        designation: form.designation.trim(),
        designation_type: form.designation_type,
        status: form.status,
      })
      setRows((current) =>
        current.map((row) => (row.emp_id === editing.emp_id ? body.data : row)),
      )
      setNotice(body.message || `Updated ${body.data?.name || editing.emp_id}.`)
      setEditing(null)
      setForm(EMPTY_EMPLOYEE_EDIT)
    } catch (err) {
      setError(apiMessage(err, 'Could not update that employee.'))
      setFieldErrors({
        name: fieldError(err, 'name'),
        email: fieldError(err, 'email'),
        sub_department: fieldError(err, 'sub_department'),
        designation: fieldError(err, 'designation'),
        designation_type: fieldError(err, 'designation_type'),
        status: fieldError(err, 'status'),
      })
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(row) {
    if (!row?.emp_id) return
    setDeletingId(row.emp_id)
    setError('')
    setNotice('')
    try {
      const body = await deleteAdminEmployee(row.emp_id)
      setRows((current) => current.filter((item) => item.emp_id !== row.emp_id))
      setCount((current) => Math.max(0, current - 1))
      if (editing?.emp_id === row.emp_id) {
        setEditing(null)
        setForm(EMPTY_EMPLOYEE_EDIT)
        setFieldErrors({})
      }
      setConfirmingId('')
      setNotice(body.message || `Deleted ${row.name || row.emp_id}.`)
    } catch (err) {
      setError(apiMessage(err, 'Could not delete that employee.'))
    } finally {
      setDeletingId('')
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const columns = useMemo(
    () => [
      { key: 'emp_id', header: 'Employee ID' },
      { key: 'name', header: 'Name' },
      {
        key: 'sub_department',
        header: 'Department',
        render: (row) => row.sub_department || '—',
      },
      {
        key: 'designation',
        header: 'Designation',
        render: (row) => row.designation || '—',
      },
      {
        key: 'status',
        header: 'Status',
        render: (row) => (
          <Badge variant={row.status === 'Active' ? 'success' : 'neutral'}>
            {row.status || '—'}
          </Badge>
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (row) => (
          <div
            className="flex items-center justify-end gap-1"
            onClick={(event) => event.stopPropagation()}
          >
            <Button
              variant="secondary"
              onClick={() => {
                setConfirmingId('')
                startEdit(row)
              }}
            >
              Edit
            </Button>
            {confirmingId === row.emp_id ? (
              <span className="ml-1 inline-flex items-center gap-2">
                <span className="text-xs text-danger-700">Delete?</span>
                <button
                  type="button"
                  className="text-xs font-medium text-danger-700 hover:underline disabled:opacity-50"
                  disabled={deletingId === row.emp_id}
                  onClick={() => handleDelete(row)}
                >
                  {deletingId === row.emp_id ? 'Deleting…' : 'Yes'}
                </button>
                <button
                  type="button"
                  className="text-xs font-medium text-ink-600 hover:underline disabled:opacity-50"
                  disabled={deletingId === row.emp_id}
                  onClick={() => setConfirmingId('')}
                >
                  No
                </button>
              </span>
            ) : (
              <button
                type="button"
                className="rounded-lg p-2 text-danger-600 hover:bg-danger-100 hover:text-danger-700 disabled:opacity-50"
                aria-label={`Delete ${row.name || row.emp_id}`}
                title="Delete"
                onClick={() => {
                  setError('')
                  setConfirmingId(row.emp_id)
                }}
              >
                <TrashIcon />
              </button>
            )}
          </div>
        ),
      },
    ],
    [confirmingId, deletingId, editing],
  )

  return (
    <section
      id="employees"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-employees"
    >
      <Card className="mt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-lg font-semibold text-ink-950">Employee</h3>
            <p className="mt-1 text-sm text-ink-600">
              Add a person, search the employee master, and correct name, department, designation,
              email, type, or status. Employee ID cannot be changed after it is created.
            </p>
          </div>
          <Button type="button" onClick={startAdd} disabled={adding || saving}>
            Add
          </Button>
        </div>
        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <TextField
            id="emp-master-filter-name"
            label="Name"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Name or employee ID…"
          />
          <label className="block" htmlFor="emp-master-filter-dept">
            <span className="text-sm font-medium text-ink-800">Department</span>
            <select
              id="emp-master-filter-dept"
              value={department}
              onChange={(event) => {
                setDepartment(event.target.value)
                setDesignation('')
              }}
              className={SELECT_CLASS}
            >
              <option value="">All departments</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {departments.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="block" htmlFor="emp-master-filter-desig">
            <span className="text-sm font-medium text-ink-800">Designation</span>
            <select
              id="emp-master-filter-desig"
              value={designation}
              onChange={(event) => setDesignation(event.target.value)}
              className={SELECT_CLASS}
            >
              <option value="">All designations</option>
              <option value={BLANK_FILTER}>(BLANK)</option>
              {designations.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>

        {adding ? (
          <form
            className="mt-4 space-y-4 rounded-xl border border-gold-200 bg-gold-100 p-4"
            onSubmit={handleAdd}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="font-display text-base font-semibold text-ink-950">Add employee</h4>
                <p className="mt-0.5 text-xs text-ink-600">
                  Employee ID, name, designation, and department. They can sign in with the default
                  password after the record exists.
                </p>
              </div>
              <Button type="button" variant="secondary" onClick={cancelEdit} disabled={saving}>
                Cancel
              </Button>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <TextField
                id="emp-master-add-empid"
                label="Employee ID"
                value={addForm.emp_id}
                onChange={(event) =>
                  setAddForm((current) => ({ ...current, emp_id: event.target.value }))
                }
                required
                error={fieldErrors.emp_id}
              />
              <TextField
                id="emp-master-add-name"
                label="Name"
                value={addForm.name}
                onChange={(event) =>
                  setAddForm((current) => ({ ...current, name: event.target.value }))
                }
                required
                error={fieldErrors.name}
              />
              <TextField
                id="emp-master-add-designation"
                label="Designation"
                value={addForm.designation}
                onChange={(event) =>
                  setAddForm((current) => ({ ...current, designation: event.target.value }))
                }
                error={fieldErrors.designation}
              />
              <TextField
                id="emp-master-add-department"
                label="Department"
                value={addForm.sub_department}
                onChange={(event) =>
                  setAddForm((current) => ({ ...current, sub_department: event.target.value }))
                }
                error={fieldErrors.sub_department}
              />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save employee'}
            </Button>
          </form>
        ) : null}

        {editing ? (
          <form
            className="mt-4 space-y-4 rounded-xl border border-gold-200 bg-gold-100 p-4"
            onSubmit={handleSave}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="font-display text-base font-semibold text-ink-950">
                  Edit {editing.name || editing.emp_id}
                </h4>
                <p className="mt-0.5 text-xs text-ink-600">
                  Employee ID {editing.emp_id} is the unique key and cannot be changed.
                </p>
              </div>
              <Button type="button" variant="secondary" onClick={cancelEdit} disabled={saving}>
                Cancel
              </Button>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <TextField
                id="emp-master-edit-empid"
                label="Employee ID"
                value={editing.emp_id}
                onChange={() => {}}
                disabled
              />
              <TextField
                id="emp-master-edit-name"
                label="Name"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                required
                error={fieldErrors.name}
              />
              <TextField
                id="emp-master-edit-email"
                label="Email"
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm((current) => ({ ...current, email: event.target.value }))
                }
                error={fieldErrors.email}
              />
              <TextField
                id="emp-master-edit-department"
                label="Department"
                value={form.sub_department}
                onChange={(event) =>
                  setForm((current) => ({ ...current, sub_department: event.target.value }))
                }
                error={fieldErrors.sub_department}
              />
              <TextField
                id="emp-master-edit-designation"
                label="Designation"
                value={form.designation}
                onChange={(event) =>
                  setForm((current) => ({ ...current, designation: event.target.value }))
                }
                error={fieldErrors.designation}
              />
              <label className="block" htmlFor="emp-master-edit-type">
                <span className="text-sm font-medium text-ink-800">Type</span>
                <select
                  id="emp-master-edit-type"
                  value={form.designation_type}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, designation_type: event.target.value }))
                  }
                  className={SELECT_CLASS}
                >
                  <option value="FACULTY">Faculty</option>
                  <option value="STAFF">Staff</option>
                </select>
                {fieldErrors.designation_type ? (
                  <span className="mt-1 block text-xs text-danger-700">
                    {fieldErrors.designation_type}
                  </span>
                ) : null}
              </label>
              <label className="block" htmlFor="emp-master-edit-status">
                <span className="text-sm font-medium text-ink-800">Status</span>
                <select
                  id="emp-master-edit-status"
                  value={form.status}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, status: event.target.value }))
                  }
                  className={SELECT_CLASS}
                >
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </select>
                {fieldErrors.status ? (
                  <span className="mt-1 block text-xs text-danger-700">{fieldErrors.status}</span>
                ) : null}
              </label>
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </form>
        ) : (
          <p className="mt-4 text-sm text-ink-600">
            Click a row or Edit to correct that employee's master record.
          </p>
        )}

        <div className="mt-3">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading employees…
            </div>
          ) : (
            <Table
              columns={columns}
              rows={rows}
              empty="No employees match those filters."
              onRowClick={startEdit}
              selectedKey={editing?.emp_id}
            />
          )}
        </div>
        {count > pageSize ? (
          <div className="mt-4 flex items-center justify-between border-t border-ink-100 pt-4">
            <p className="text-xs text-ink-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={page <= 1 || loading}
                onClick={() => setPage((n) => n - 1)}
              >
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
    </section>
  )
}

function EmployeeApproverSection() {
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('')
  const [designation, setDesignation] = useState('')
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [page, setPage] = useState(1)
  const [rows, setRows] = useState([])
  const [count, setCount] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyKey, setBusyKey] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    async function loadEaDepartmentOptions() {
      try {
        const body = await fetchAdminEmployeeFilters()
        setDepartments(body.data.departments || [])
      } catch {
        setDepartments([])
      }
    }
    loadEaDepartmentOptions()
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadEaDesignations() {
      try {
        const body = await fetchAdminEmployeeFilters({ department })
        if (!cancelled) {
          const next = body.data.designations || []
          setDesignations(next)
          setDesignation((current) => (current && next.includes(current) ? current : ''))
        }
      } catch {
        if (!cancelled) setDesignations([])
      }
    }
    loadEaDesignations()
    return () => {
      cancelled = true
    }
  }, [department])

  useEffect(() => {
    setPage(1)
  }, [query, department, designation])

  useEffect(() => {
    let cancelled = false
    const handle = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const body = await fetchEmployeeApprovers({
          q: query.trim() || undefined,
          department,
          designation,
          page,
          pageSize: 500,
        })
        if (!cancelled) {
          setRows(
            (body.data.results || []).map((row) => ({
              ...row,
              rowKey: row.employee?.emp_id,
            })),
          )
          setCount(body.data.count || 0)
          setPageSize(body.data.page_size || 50)
        }
      } catch (err) {
        if (!cancelled) {
          setError(apiMessage(err, 'Could not load employees.'))
          setRows([])
          setCount(0)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, query.trim() ? 200 : 0)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [query, department, designation, page])

  async function clearSlot(row, payload, actionKey) {
    if (!row.id) return
    setError('')
    setNotice('')
    setBusyKey(actionKey)
    try {
      const body = await patchEmployeeApprover(row.id, payload)
      const name = row.employee?.name || row.employee?.emp_id
      const next = body.data || {
        ...row,
        id: null,
        approver_1: payload.clear_approver_1 ? null : row.approver_1,
        approver_2: payload.clear_approver_2 ? null : row.approver_2,
      }
      setRows((current) =>
        current.map((item) =>
          item.employee?.emp_id === row.employee?.emp_id
            ? { ...item, ...next, rowKey: row.employee?.emp_id }
            : item,
        ),
      )
      const slot = payload.clear_approver_1 ? 'Approver 1' : 'Approver 2'
      setNotice(body.message || `Removed ${slot} for ${name}.`)
    } catch (err) {
      setError(apiMessage(err, 'Could not update that mapping.'))
    } finally {
      setBusyKey('')
    }
  }

  async function handleDownload() {
    setError('')
    setNotice('')
    setExporting(true)
    try {
      await exportEmployeeApprovers({
        q: query.trim() || undefined,
        department,
        designation,
      })
    } catch (err) {
      setError(apiMessage(err, 'Could not download the spreadsheet.'))
    } finally {
      setExporting(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const employeeApproverColumns = useMemo(
    () => [
      {
        key: 'emp_id',
        header: 'Employee ID',
        render: (row) => row.employee?.emp_id || '—',
      },
      {
        key: 'name',
        header: 'Name',
        render: (row) => row.employee?.name || '—',
      },
      {
        key: 'sub_department',
        header: 'Department',
        render: (row) => row.employee?.sub_department || '—',
      },
      {
        key: 'designation',
        header: 'Designation',
        render: (row) => row.employee?.designation || '—',
      },
      {
        key: 'approver_1',
        header: 'Approver 1',
        render: (row) =>
          isHodTitle(row) ? (
            <span className="text-ink-800">{hodApproverLabel()}</span>
          ) : (
            <ApproverChip
              person={row.approver_1}
              busy={busyKey === `ea-a1-${row.employee?.emp_id}`}
              disabled={Boolean(busyKey)}
              slotLabel="Approver 1"
              onClick={() =>
                clearSlot(row, { clear_approver_1: true }, `ea-a1-${row.employee?.emp_id}`)
              }
            />
          ),
      },
      {
        key: 'approver_2',
        header: 'Approver 2',
        render: (row) =>
          isHodTitle(row) ? (
            <span className="text-ink-400">—</span>
          ) : (
            <ApproverChip
              person={row.approver_2}
              busy={busyKey === `ea-a2-${row.employee?.emp_id}`}
              disabled={Boolean(busyKey)}
              slotLabel="Approver 2"
              onClick={() =>
                clearSlot(row, { clear_approver_2: true }, `ea-a2-${row.employee?.emp_id}`)
              }
            />
          ),
      },
    ],
    [busyKey],
  )

  return (
    <section
      id="employee-approvers"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-employee-approvers"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Employee-Approver</h3>
        <p className="mt-1 text-sm text-ink-600">
          Every employee is listed. If the designation contains HOD, the only approver is the
          Vice-Chancellor — Approver 1 and Approver 2 stay unused. For other staff, Approver 1
          is required for a personal mapping; Approver 2 is optional. Removing a name affects
          only that employee; staff leave then uses the department assignment, then the
          Vice-Chancellor.
        </p>
        {error ? <p className="mt-3 text-sm text-danger-700">{error}</p> : null}
        {notice ? <p className="mt-3 text-sm text-success-700">{notice}</p> : null}

        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="grid min-w-0 flex-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <TextField
              id="ea-filter-name"
              label="Name"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name or employee ID…"
            />
            <label className="block" htmlFor="ea-filter-dept">
              <span className="text-sm font-medium text-ink-800">Department</span>
              <select
                id="ea-filter-dept"
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
            <label className="block" htmlFor="ea-filter-desig">
              <span className="text-sm font-medium text-ink-800">Designation</span>
              <select
                id="ea-filter-desig"
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
          </div>
          <Button disabled={exporting || loading} onClick={handleDownload}>
            {exporting ? 'Downloading…' : 'Download'}
          </Button>
        </div>

        <p className="mt-4 text-sm text-ink-600">
          Click an approver's name to remove a wrong assignment.
        </p>

        <div className="mt-3">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading employees…
            </div>
          ) : (
            <Table
              columns={employeeApproverColumns}
              rows={rows}
              empty="No employees match those filters."
            />
          )}
        </div>
        {count > pageSize ? (
          <div className="mt-4 flex items-center justify-between border-t border-ink-100 pt-4">
            <p className="text-xs text-ink-500">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={page <= 1 || loading}
                onClick={() => setPage((n) => n - 1)}
              >
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
    </section>
  )
}

function ResetPasswordSection() {
  const [employee, setEmployee] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  function clearMessages() {
    setFormError('')
    setSuccess('')
    setFieldErrors({})
  }

  async function handleSubmit(event) {
    event.preventDefault()
    clearMessages()

    if (!employee?.emp_id) {
      setFormError('Search and select the employee whose password you are resetting.')
      return
    }
    if (newPassword !== confirmPassword) {
      setFieldErrors({ confirm_password: 'Passwords do not match.' })
      return
    }

    setSubmitting(true)
    try {
      const body = await resetAdminEmployeePassword(employee.emp_id, {
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setNewPassword('')
      setConfirmPassword('')
      setSuccess(
        body.message ||
          `Password reset for ${employee.name} (${employee.emp_id}). They can sign in with the new password and will be asked to change it.`,
      )
    } catch (err) {
      setFormError(apiMessage(err, 'Could not reset that password.'))
      setFieldErrors({
        new_password: fieldError(err, 'new_password'),
        confirm_password: fieldError(err, 'confirm_password'),
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section
      id="change-password"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-change-password"
    >
      <Card className="mt-6 max-w-xl">
        <h3 className="font-display text-lg font-semibold text-ink-950">Change password</h3>
        <p className="mt-1 text-sm text-ink-600">
          Assign a new password when someone has forgotten theirs. Search by name or employee ID.
          They will sign in with this password and then be asked to set their own. Use at least 8
          characters. The default password is not allowed.
        </p>
        <form className="mt-4 space-y-4" onSubmit={handleSubmit} autoComplete="off">
          {formError ? (
            <p className="rounded-lg bg-danger-100 px-3 py-2 text-sm text-danger-700">{formError}</p>
          ) : null}
          {success ? (
            <p className="rounded-lg bg-success-100 px-3 py-2 text-sm text-success-700">{success}</p>
          ) : null}
          <EmployeeFinder
            id="reset-employee"
            label="Employee ID or name"
            value={employee}
            onChange={(next) => {
              setEmployee(next)
              clearMessages()
            }}
          />
          <TextField
            id="reset-new-password"
            label="New password"
            type="password"
            value={newPassword}
            onChange={(event) => {
              setNewPassword(event.target.value)
              clearMessages()
            }}
            autoComplete="new-password"
            required
            error={fieldErrors.new_password}
          />
          <TextField
            id="reset-confirm-password"
            label="Confirm new password"
            type="password"
            value={confirmPassword}
            onChange={(event) => {
              setConfirmPassword(event.target.value)
              clearMessages()
            }}
            autoComplete="new-password"
            required
            error={fieldErrors.confirm_password}
          />
          <Button type="submit" disabled={submitting || !employee}>
            {submitting ? 'Saving…' : 'Assign password'}
          </Button>
        </form>
      </Card>
    </section>
  )
}

function LeaveTypesSection() {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState(EMPTY_LEAVE)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [savingId, setSavingId] = useState(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const body = await fetchAdminLeaveTypes()
      setRows(body.data)
    } catch (err) {
      setError(apiMessage(err, 'Could not load leave types.'))
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
      setForm(EMPTY_LEAVE)
      await load()
    } catch (err) {
      setError(apiMessage(err, 'Could not create that leave type.'))
    } finally {
      setBusy(false)
    }
  }

  function updateRow(id, patch) {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  async function saveRow(row) {
    setSavingId(row.id)
    setError('')
    try {
      const cap = row.max_days_per_year
      const body = await patchAdminLeaveType(row.id, {
        name: row.name,
        applicable_to: row.applicable_to,
        is_active: row.is_active,
        max_days_per_year: cap === '' || cap == null ? null : Number(cap),
      })
      setRows((current) => current.map((item) => (item.id === row.id ? body.data : item)))
    } catch (err) {
      setError(apiMessage(err, 'Could not update that leave type.'))
    } finally {
      setSavingId(null)
    }
  }

  const columns = useMemo(
    () => [
      { key: 'code', header: 'Code' },
      {
        key: 'name',
        header: 'Name',
        render: (row) => (
          <input
            aria-label={`${row.code} name`}
            value={row.name}
            onChange={(event) => updateRow(row.id, { name: event.target.value })}
            className="w-40 rounded-lg border border-ink-300 bg-paper-raised px-2 py-1.5 text-sm"
          />
        ),
      },
      {
        key: 'applicable_to',
        header: 'Applies to',
        render: (row) => (
          <select
            aria-label={`${row.code} applies to`}
            value={row.applicable_to}
            onChange={(event) => updateRow(row.id, { applicable_to: event.target.value })}
            className="rounded-lg border border-ink-300 bg-paper-raised px-2 py-1.5 text-sm"
          >
            <option value="ALL">All</option>
            <option value="FACULTY">Faculty</option>
            <option value="STAFF">Staff</option>
          </select>
        ),
      },
      {
        key: 'max_days_per_year',
        header: 'Yearly cap',
        render: (row) => (
          <input
            aria-label={`${row.code} yearly cap`}
            type="number"
            min="0"
            value={row.max_days_per_year ?? ''}
            placeholder="None"
            onChange={(event) => updateRow(row.id, { max_days_per_year: event.target.value })}
            className="w-24 rounded-lg border border-ink-300 bg-paper-raised px-2 py-1.5 text-sm"
          />
        ),
      },
      {
        key: 'is_active',
        header: 'Active',
        render: (row) => (
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={Boolean(row.is_active)}
              onChange={(event) => updateRow(row.id, { is_active: event.target.checked })}
            />
            <Badge variant={row.is_active ? 'success' : 'neutral'}>
              {row.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </label>
        ),
      },
      {
        key: 'actions',
        header: '',
        render: (row) => (
          <Button
            variant="secondary"
            disabled={savingId === row.id}
            onClick={() => saveRow(row)}
          >
            {savingId === row.id ? 'Saving…' : 'Save'}
          </Button>
        ),
      },
    ],
    [savingId],
  )

  return (
    <section
      id="leave-types"
      className="scroll-mt-6"
      role="tabpanel"
      aria-labelledby="settings-tab-leave-types"
    >
      <Card className="mt-6">
        <h3 className="font-display text-lg font-semibold text-ink-950">Leave type</h3>
        <p className="mt-1 text-sm text-ink-600">
          Set the yearly cap, who the type applies to, and whether it is offered on the apply
          form.
        </p>

        <form className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5" onSubmit={handleCreate}>
          <TextField
            id="leave-type-name"
            label="Name"
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            required
          />
          <TextField
            id="leave-type-code"
            label="Code"
            value={form.code}
            onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
            required
          />
          <label className="block" htmlFor="leave-type-applies">
            <span className="text-sm font-medium text-ink-800">Applies to</span>
            <select
              id="leave-type-applies"
              value={form.applicable_to}
              onChange={(event) =>
                setForm((current) => ({ ...current, applicable_to: event.target.value }))
              }
              className={SELECT_CLASS}
            >
              <option value="ALL">All</option>
              <option value="FACULTY">Faculty</option>
              <option value="STAFF">Staff</option>
            </select>
          </label>
          <TextField
            id="leave-type-cap"
            label="Yearly cap"
            type="number"
            value={form.max_days_per_year}
            onChange={(event) =>
              setForm((current) => ({ ...current, max_days_per_year: event.target.value }))
            }
          />
          <div className="flex items-end">
            <Button type="submit" disabled={busy}>
              {busy ? 'Saving…' : 'Add leave type'}
            </Button>
          </div>
        </form>

        {error ? <p className="mt-4 text-sm text-danger-700">{error}</p> : null}

        <div className="mt-4">
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-ink-600">
              <LoadingSpinner size={16} />
              Loading leave types…
            </div>
          ) : (
            <Table columns={columns} rows={rows} empty="No leave types yet." />
          )}
        </div>
      </Card>
    </section>
  )
}
