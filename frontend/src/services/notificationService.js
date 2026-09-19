import apiClient from './apiClient'

export async function fetchNotifications({ page = 1 } = {}) {
  const response = await apiClient.get('/notifications/', {
    params: { page: page || undefined },
  })
  return response.data
}

export async function markNotificationRead(id) {
  const path = id ? `/notifications/${id}/read/` : '/notifications/read/'
  const response = await apiClient.post(path)
  return response.data
}
