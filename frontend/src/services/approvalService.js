import apiClient from './apiClient'

export async function fetchApprovalInbox({ page = 1 } = {}) {
  const response = await apiClient.get('/approvals/', {
    params: { page: page || undefined },
  })
  return response.data
}

export async function decideApproval(id, payload) {
  const response = await apiClient.post(`/approvals/${id}/decide/`, payload)
  return response.data
}

export async function fetchApprovalEmployeeLeaves(id, { page = 1, pageSize = 8 } = {}) {
  const response = await apiClient.get(`/approvals/${id}/employee-leaves/`, {
    params: {
      page: page || undefined,
      page_size: pageSize || undefined,
    },
  })
  return response.data
}
