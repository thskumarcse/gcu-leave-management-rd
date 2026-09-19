import { Navigate, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/auth/Login'
import ChangePassword from './pages/auth/ChangePassword'
import Directory from './pages/employee/Directory'
import Profile from './pages/employee/Profile'
import EmployeeDetail from './pages/employee/EmployeeDetail'
import ApplyLeave from './pages/employee/ApplyLeave'
import MyLeaves from './pages/employee/MyLeaves'
import ApprovalsInbox from './pages/approvals/Inbox'
import ApproverDashboard from './pages/approvals/Dashboard'
import Notifications from './pages/Notifications'
import Settings from './pages/admin/Settings'
import Analytics from './pages/admin/Analytics'
import AdminEmployees from './pages/admin/Employees'
import AdminLeaveTypes from './pages/admin/LeaveTypes'
import AdminApprovers from './pages/admin/Approvers'
import AdminReports from './pages/admin/Reports'
import AdminAudit from './pages/admin/Audit'
import RequireAuth from './routes/RequireAuth'
import RequireAdmin from './routes/RequireAdmin'
import RequireAdminOnly from './routes/RequireAdminOnly'
import RequireApprover from './routes/RequireApprover'

function Protected({ children }) {
  return <RequireAuth>{children}</RequireAuth>
}

function RedirectToAnalytics() {
  return <Navigate to={`/analytics${window.location.hash}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ChangePassword />} />
      <Route path="/" element={<Protected><Home /></Protected>} />
      <Route path="/profile" element={<Protected><Profile /></Protected>} />
      <Route
        path="/employees"
        element={
          <Protected>
            <RequireAdmin>
              <Directory />
            </RequireAdmin>
          </Protected>
        }
      />
      <Route path="/employees/:empId" element={<Protected><EmployeeDetail /></Protected>} />
      <Route path="/leaves" element={<Protected><MyLeaves /></Protected>} />
      <Route path="/leaves/apply" element={<Protected><ApplyLeave /></Protected>} />
      <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
      <Route
        path="/approvals"
        element={
          <Protected>
            <RequireApprover>
              <ApprovalsInbox />
            </RequireApprover>
          </Protected>
        }
      />
      <Route
        path="/approvals/dashboard"
        element={
          <Protected>
            <RequireApprover>
              <ApproverDashboard />
            </RequireApprover>
          </Protected>
        }
      />
      <Route
        path="/settings"
        element={
          <Protected>
            <RequireAdminOnly>
              <Settings />
            </RequireAdminOnly>
          </Protected>
        }
      />
      <Route
        path="/analytics"
        element={
          <Protected>
            <RequireAdmin>
              <Analytics />
            </RequireAdmin>
          </Protected>
        }
      />
      <Route
        path="/admin"
        element={
          <Protected>
            <RequireAdmin>
              <RedirectToAnalytics />
            </RequireAdmin>
          </Protected>
        }
      />
      <Route
        path="/admin/employees"
        element={
          <Protected>
            <RequireAdminOnly>
              <AdminEmployees />
            </RequireAdminOnly>
          </Protected>
        }
      />
      <Route
        path="/admin/leave-types"
        element={
          <Protected>
            <RequireAdminOnly>
              <AdminLeaveTypes />
            </RequireAdminOnly>
          </Protected>
        }
      />
      <Route
        path="/admin/approvers"
        element={
          <Protected>
            <RequireAdminOnly>
              <AdminApprovers />
            </RequireAdminOnly>
          </Protected>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <Protected>
            <RequireAdmin>
              <AdminReports />
            </RequireAdmin>
          </Protected>
        }
      />
      <Route
        path="/admin/audit"
        element={
          <Protected>
            <RequireAdmin>
              <AdminAudit />
            </RequireAdmin>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
