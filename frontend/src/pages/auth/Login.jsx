import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import BrandHeader from '../../components/layout/BrandHeader'
import Card from '../../components/common/Card'
import Button from '../../components/common/Button'
import LoadingSpinner from '../../components/common/LoadingSpinner'
import TextField from '../../components/forms/TextField'
import { useAuth } from '../../context/auth-context'

function fieldError(err, field) {
  const errors = err?.response?.data?.errors
  if (!errors) return ''
  const value = errors[field]
  if (Array.isArray(value)) return value[0]
  return value || ''
}

export default function Login() {
  const { user, ready, login } = useAuth()
  const navigate = useNavigate()
  const [empId, setEmpId] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper">
        <LoadingSpinner />
      </div>
    )
  }

  if (user?.must_change_password) {
    return <Navigate to="/change-password" replace />
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFieldErrors({})
    setSubmitting(true)
    try {
      const nextUser = await login(empId.trim(), password)
      navigate(nextUser.must_change_password ? '/change-password' : '/', { replace: true })
    } catch (err) {
      setFormError(err?.response?.data?.message || 'Could not sign in. Try again.')
      setFieldErrors({
        emp_id: fieldError(err, 'emp_id'),
        password: fieldError(err, 'password'),
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <BrandHeader />
      <main className="mx-auto flex max-w-5xl justify-center px-6 py-12">
        <Card className="w-full max-w-md">
          <h2 className="font-display text-2xl font-semibold text-ink-950">Sign in</h2>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            {formError ? (
              <p className="rounded-lg bg-danger-100 px-3 py-2 text-sm text-danger-700">{formError}</p>
            ) : null}

            <TextField
              id="emp_id"
              label="Employee ID"
              value={empId}
              onChange={(event) => setEmpId(event.target.value)}
              autoComplete="username"
              required
              placeholder="e.g. GCU001"
              error={fieldErrors.emp_id}
            />
            <TextField
              id="password"
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              error={fieldErrors.password}
            />

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </Card>
      </main>
    </div>
  )
}
