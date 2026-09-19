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
  return typeof value === 'string' ? value : value?.[0] || ''
}

export default function ChangePassword() {
  const { user, ready, changePassword, logout } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
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

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!user.must_change_password) {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')
    setFieldErrors({})

    if (newPassword !== confirmPassword) {
      setFieldErrors({ confirm_password: 'Passwords do not match.' })
      return
    }

    setSubmitting(true)
    try {
      await changePassword({ currentPassword, newPassword, confirmPassword })
      navigate('/', { replace: true })
    } catch (err) {
      setFormError(err?.response?.data?.message || 'Could not update the password.')
      setFieldErrors({
        current_password: fieldError(err, 'current_password'),
        new_password: fieldError(err, 'new_password'),
        confirm_password: fieldError(err, 'confirm_password'),
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSignOut() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-paper">
      <BrandHeader
        right={
          <button
            type="button"
            onClick={handleSignOut}
            className="text-sm text-ink-300 transition-colors hover:text-white"
          >
            Sign out
          </button>
        }
      />
      <main className="mx-auto flex max-w-5xl justify-center px-6 py-12">
        <Card className="w-full max-w-md">
          <h2 className="font-display text-2xl font-semibold text-ink-950">Set a new password</h2>
          <p className="mt-2 text-sm text-ink-700">
            Welcome{user.name ? `, ${user.name}` : ''}. You signed in with the default password,
            so you must choose a new one before using the system.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            {formError ? (
              <p className="rounded-lg bg-danger-100 px-3 py-2 text-sm text-danger-700">{formError}</p>
            ) : null}

            <TextField
              id="current_password"
              label="Current password"
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              autoComplete="current-password"
              required
              error={fieldErrors.current_password}
            />
            <TextField
              id="new_password"
              label="New password"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              autoComplete="new-password"
              required
              error={fieldErrors.new_password}
            />
            <TextField
              id="confirm_password"
              label="Confirm new password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              required
              error={fieldErrors.confirm_password}
            />

            <p className="text-xs text-ink-500">
              Use at least 8 characters. The default password is not allowed.
            </p>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Saving…' : 'Save password'}
            </Button>
          </form>
        </Card>
      </main>
    </div>
  )
}
