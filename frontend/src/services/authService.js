import apiClient from './apiClient'

export async function loginRequest(empId, password) {
  const response = await apiClient.post('/auth/login/', {
    emp_id: empId,
    password,
  })
  return response.data
}

export async function changePasswordRequest({ currentPassword, newPassword, confirmPassword }) {
  const response = await apiClient.post('/auth/change-password/', {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  })
  return response.data
}

export async function fetchCurrentUser() {
  const response = await apiClient.get('/auth/me/')
  return response.data
}

export async function logoutRequest(refresh) {
  try {
    await apiClient.post('/auth/logout/', { refresh })
  } catch {
    // Clearing local session still signs the browser out even if the
    // blacklist call fails (expired token, network, etc.).
  }
}
