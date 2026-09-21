import { useEffect, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import { fetchEmployee } from '../../services/employeeService'
import { ProfileCard } from './Profile'
import { useAuth } from '../../context/auth-context'

export default function EmployeeDetail() {
  const { empId } = useParams()
  const { user } = useAuth()
  const [employee, setEmployee] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const body = await fetchEmployee(empId)
        if (!cancelled) setEmployee(body.data)
      } catch (err) {
        if (!cancelled) {
          setEmployee(null)
          setError(err?.response?.data?.message || 'Employee not found.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [empId])

  const isSelf = user?.emp_id && empId && user.emp_id.toLowerCase() === empId.toLowerCase()
  const canBrowseDirectory = Boolean(user?.is_admin || user?.is_operator)

  if (!isSelf && !canBrowseDirectory) {
    return <Navigate to="/" replace />
  }

  return (
    <>
      {canBrowseDirectory ? (
        <Link to="/employees" className="text-sm font-medium text-ink-700 hover:text-ink-950">
          ← Directory
        </Link>
      ) : null}
      <h2 className="mt-4 font-display text-2xl font-semibold text-ink-950">Employee record</h2>
      <p className="mt-1 text-sm text-ink-700">
        {isSelf
          ? 'This is your master record, including contact details.'
          : 'Contact numbers and date of birth are only visible on your own profile.'}
      </p>

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-ink-600">
            <LoadingSpinner size={16} />
            Loading employee…
          </div>
        ) : null}
        {error ? <p className="text-sm text-danger-700">{error}</p> : null}
        {employee ? <ProfileCard employee={employee} showSensitive={Boolean(employee.dob)} /> : null}
      </div>
    </>
  )
}
