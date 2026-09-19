import apiClient from './apiClient'

export async function fetchMyEmployee() {
  const response = await apiClient.get('/employees/me/')
  return response.data
}

export async function fetchEmployees({ q = '', groupName = '', page = 1 } = {}) {
  const response = await apiClient.get('/employees/', {
    params: {
      q: q || undefined,
      group_name: groupName || undefined,
      page: page || undefined,
    },
  })
  return response.data
}

export async function fetchEmployee(empId) {
  const response = await apiClient.get(`/employees/${empId}/`)
  return response.data
}
