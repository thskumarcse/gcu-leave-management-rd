import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/auth-context'

export default function RequireAdmin({ children }) {
  const { user } = useAuth()
  if (!(user?.is_admin || user?.is_operator)) {
    return <Navigate to="/" replace />
  }
  return children
}
