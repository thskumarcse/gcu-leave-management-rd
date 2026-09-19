import { Navigate } from 'react-router-dom'
import LoadingSpinner from '../components/common/LoadingSpinner'
import { useAuth } from '../context/auth-context'

export default function RequireAuth({ children }) {
  const { user, ready } = useAuth()

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

  if (user.must_change_password) {
    return <Navigate to="/change-password" replace />
  }

  return children
}
