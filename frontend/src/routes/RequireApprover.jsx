import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/auth-context'

export default function RequireApprover({ children }) {
  const { user } = useAuth()
  if (!(user?.is_hod || user?.is_vc || user?.is_approver)) {
    return <Navigate to="/" replace />
  }
  return children
}
