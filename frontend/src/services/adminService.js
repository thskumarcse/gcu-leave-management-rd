import apiClient from './apiClient'

export async function fetchAdminOverview() {
  const response = await apiClient.get('/admin/overview/')
  return response.data
}

function unitQuery(params) {
  return params.subDepartment || params.department || undefined
}

export async function fetchAdminEmployees(params = {}) {
  const unit = unitQuery(params)
  const response = await apiClient.get('/admin/employees/', {
    params: {
      q: params.q || undefined,
      status: params.status || undefined,
      group_name: params.groupName || undefined,
      sub_department: unit,
      department: unit,
      designation: params.designation || undefined,
      designation_type: params.designationType || undefined,
      is_admin: params.isAdmin ? true : undefined,
      is_operator: params.isOperator ? true : undefined,
      page: params.page || undefined,
      page_size: params.pageSize || undefined,
    },
  })
  return response.data
}

export async function fetchAdminEmployeeFilters(params = {}) {
  const unit = unitQuery(params)
  const response = await apiClient.get('/admin/employees/filters/', {
    params: {
      sub_department: unit,
      department: unit,
    },
  })
  return response.data
}

export async function createAdminEmployee(payload) {
  const response = await apiClient.post('/admin/employees/', payload)
  return response.data
}

export async function patchAdminEmployee(empId, payload) {
  const response = await apiClient.patch(`/admin/employees/${empId}/`, payload)
  return response.data
}

export async function patchAdminAccess(empId, payload) {
  const response = await apiClient.patch(`/admin/access/${empId}/`, payload)
  return response.data
}

export async function fetchAssignLeaveGrants() {
  const response = await apiClient.get('/admin/assign-leave/')
  return response.data
}

export async function createAssignLeave(payload) {
  const response = await apiClient.post('/admin/assign-leave/', payload)
  return response.data
}

export async function deleteAdminEmployee(empId) {
  const response = await apiClient.delete(`/admin/employees/${empId}/`)
  return response.data
}

export async function resetAdminEmployeePassword(empId, payload) {
  const response = await apiClient.post(`/admin/employees/${empId}/reset-password/`, payload)
  return response.data
}

export async function fetchAdminLeaveTypes() {
  const response = await apiClient.get('/admin/leave-types/')
  return response.data
}

export async function createAdminLeaveType(payload) {
  const response = await apiClient.post('/admin/leave-types/', payload)
  return response.data
}

export async function patchAdminLeaveType(id, payload) {
  const response = await apiClient.patch(`/admin/leave-types/${id}/`, payload)
  return response.data
}

export async function fetchAdminApprovers() {
  const response = await apiClient.get('/admin/approvers/')
  return response.data
}

export async function createAdminApprover(payload) {
  const response = await apiClient.post('/admin/approvers/', payload)
  return response.data
}

export async function deleteAdminApprover(id) {
  const response = await apiClient.delete(`/admin/approvers/${id}/`)
  return response.data
}

export async function assignEmployeeStaffApprovers(payload) {
  const response = await apiClient.post('/admin/employee-approvers/', payload)
  return response.data
}

function employeeApproverParams(params = {}) {
  const unit = unitQuery(params)
  return {
    q: params.q || undefined,
    sub_department: unit,
    department: unit,
    designation: params.designation || undefined,
    page: params.page || undefined,
    page_size: params.pageSize || undefined,
  }
}

async function downloadExcelBlob(response, fallbackName) {
  const type = response.headers['content-type'] || ''
  if (type.includes('application/json')) {
    const text = await response.data.text()
    const body = JSON.parse(text)
    const error = new Error(body.message || 'Could not download the spreadsheet.')
    error.response = { data: body }
    throw error
  }
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  const disposition = response.headers['content-disposition'] || ''
  const match = disposition.match(/filename="?([^"]+)"?/i)
  link.href = url
  link.download = match?.[1] || fallbackName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function fetchEmployeeApprovers(params = {}) {
  const response = await apiClient.get('/admin/employee-approvers/', {
    params: employeeApproverParams(params),
  })
  return response.data
}

export async function exportEmployeeApprovers(params = {}) {
  const response = await apiClient.get('/admin/employee-approvers/export/', {
    params: employeeApproverParams(params),
    responseType: 'blob',
  })
  await downloadExcelBlob(response, 'employee-approvers.xlsx')
  return response
}

export async function patchEmployeeApprover(id, payload) {
  const response = await apiClient.patch(`/admin/employee-approvers/${id}/`, payload)
  return response.data
}

export async function deleteEmployeeApprover(id) {
  const response = await apiClient.delete(`/admin/employee-approvers/${id}/`)
  return response.data
}

export async function fetchAdminReport({ year } = {}) {
  const response = await apiClient.get('/admin/reports/', {
    params: { year: year || undefined },
  })
  return response.data
}

export async function fetchAdminAudit({ page = 1 } = {}) {
  const response = await apiClient.get('/admin/audit/', {
    params: { page: page || undefined },
  })
  return response.data
}

function leaveFilterParams(params) {
  const unit = unitQuery(params)
  return {
    q: params.q || undefined,
    sub_department: unit,
    department: unit,
    designation: params.designation || undefined,
    start: params.start || undefined,
    end: params.end || undefined,
    page: params.page || undefined,
    page_size: params.pageSize || undefined,
  }
}

export async function fetchAdminLeaves(params = {}) {
  const response = await apiClient.get('/admin/leaves/', {
    params: leaveFilterParams(params),
  })
  return response.data
}

export async function exportAdminLeaves(params = {}) {
  const response = await apiClient.get('/admin/leaves/export/', {
    params: leaveFilterParams(params),
    responseType: 'blob',
  })
  await downloadExcelBlob(response, 'leave-applications.xlsx')
  return response
}
