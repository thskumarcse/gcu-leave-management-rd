import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
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
import AppShell from './layouts/AppShell'
import RequireAuth from './routes/RequireAuth'
import RequireAdmin from './routes/RequireAdmin'
import RequireAdminOnly from './routes/RequireAdminOnly'
import RequireApprover from './routes/RequireApprover'

function ProtectedShell() {
  return (
    <RequireAuth>
      <AppShell>
        <Outlet />
      </AppShell>
    </RequireAuth>
  )
}

function RedirectToAnalytics() {
  return <Navigate to={`/analytics${window.location.hash}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/change-password" element={<ChangePassword />} />
      <Route element={<ProtectedShell />}>
        <Route path="/" element={<Home />} />
        <Route path="/profile" element={<Profile />} />
        <Route
          path="/employees"
          element={
            <RequireAdmin>
              <Directory />
            </RequireAdmin>
          }
        />
        <Route path="/employees/:empId" element={<EmployeeDetail />} />
        <Route path="/leaves" element={<MyLeaves />} />
        <Route path="/leaves/apply" element={<ApplyLeave />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route
          path="/approvals"
          element={
            <RequireApprover>
              <ApprovalsInbox />
            </RequireApprover>
          }
        />
        <Route
          path="/approvals/dashboard"
          element={
            <RequireApprover>
              <ApproverDashboard />
            </RequireApprover>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAdminOnly>
              <Settings />
            </RequireAdminOnly>
          }
        />
        <Route
          path="/analytics"
          element={
            <RequireAdmin>
              <Analytics />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <RedirectToAnalytics />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/employees"
          element={
            <RequireAdminOnly>
              <AdminEmployees />
            </RequireAdminOnly>
          }
        />
        <Route
          path="/admin/leave-types"
          element={
            <RequireAdminOnly>
              <AdminLeaveTypes />
            </RequireAdminOnly>
          }
        />
        <Route
          path="/admin/approvers"
          element={
            <RequireAdminOnly>
              <AdminApprovers />
            </RequireAdminOnly>
          }
        />
        <Route
          path="/admin/reports"
          element={
            <RequireAdmin>
              <AdminReports />
            </RequireAdmin>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <RequireAdmin>
              <AdminAudit />
            </RequireAdmin>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
