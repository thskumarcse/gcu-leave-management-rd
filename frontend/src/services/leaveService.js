import apiClient from './apiClient'

export async function fetchLeaveTypes() {
  const response = await apiClient.get('/leave-types/')
  return response.data
}

export async function fetchLeaveSummary() {
  const response = await apiClient.get('/leaves/summary/')
  return response.data
}

export async function fetchLeaves({ status = '', page = 1 } = {}) {
  const response = await apiClient.get('/leaves/', {
    params: {
      status: status || undefined,
      page: page || undefined,
    },
  })
  return response.data
}

export async function applyLeave(payload) {
  const response = await apiClient.post('/leaves/', payload)
  return response.data
}

export async function cancelLeave(id) {
  const response = await apiClient.post(`/leaves/${id}/cancel/`)
  return response.data
}
