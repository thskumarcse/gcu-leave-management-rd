import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/auth-context'

export default function RequireAdminOnly({ children }) {
  const { user } = useAuth()
  if (!user?.is_admin) {
    return <Navigate to="/" replace />
  }
  return children
}
