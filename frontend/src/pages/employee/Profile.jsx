import { useEffect, useState } from 'react'
import Card from '../../components/common/Card'
import Badge from '../../components/common/Badge'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import { fetchMyEmployee } from '../../services/employeeService'
import { formatDate } from '../../utils/formatDate'

export default function Profile() {
  const [employee, setEmployee] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const body = await fetchMyEmployee()
        if (!cancelled) setEmployee(body.data)
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.message || 'Could not load your employee record.')
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
    <>
      <div className="mb-6">
        <h2 className="font-display text-2xl font-semibold text-ink-950">My profile</h2>
        <p className="mt-1 text-sm text-ink-700">
          This is your record from the university employee master. It is not edited from this
          screen.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-ink-600">
          <LoadingSpinner size={16} />
          Loading profile…
        </div>
      ) : null}

      {error ? <p className="text-sm text-danger-700">{error}</p> : null}

      {employee ? <ProfileCard employee={employee} showSensitive /> : null}
    </>
  )
}

export function ProfileCard({ employee, showSensitive = false }) {
  const fields = [
    ['Employee ID', employee.emp_id],
    ['Name', employee.name],
    ['Department', employee.sub_department],
    ['School', employee.department],
    ['Designation', employee.designation],
    ['Group', employee.group_name || employee.designation_type],
    ['User type', employee.user_type],
    ['Academy', employee.academy],
    ['Email', employee.email],
    ['Joined', formatDate(employee.joining_date)],
  ]

  if (showSensitive) {
    fields.push(['Mobile', employee.mobile], ['Date of birth', formatDate(employee.dob)])
  }

  return (
    <Card className="max-w-2xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-lg font-semibold text-ink-950">{employee.name}</h3>
          <p className="mt-1 text-sm text-ink-600">{employee.emp_id}</p>
        </div>
        <Badge variant={employee.status === 'Active' ? 'success' : 'danger'} dot>
          {employee.status}
        </Badge>
      </div>
      <dl className="mt-5 grid grid-cols-1 gap-4 border-t border-ink-100 pt-5 sm:grid-cols-2">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</dt>
            <dd className="mt-1 text-sm font-medium text-ink-950">{value || '—'}</dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}
