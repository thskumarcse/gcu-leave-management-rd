import apiClient from './apiClient'

export async function fetchApproverDashboard() {
  const response = await apiClient.get('/dashboard/')
  return response.data
}
