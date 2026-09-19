import axios from 'axios'
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  persistSession,
} from '../utils/authStorage'

export const SESSION_EXPIRED_EVENT = 'gcu:session-expired'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

let refreshPromise = null
let sessionExpired = false

function isAnonymousAuthRequest(config) {
  const url = config?.url || ''
  return url.includes('/auth/refresh/') || url.includes('/auth/login/')
}

function sessionExpiredError(config) {
  const err = new Error('Session expired')
  err.config = config
  err.isSessionExpired = true
  return err
}

export function resetSessionGuard() {
  sessionExpired = false
}

function expireSession() {
  refreshPromise = null
  clearSession()
  if (sessionExpired) return
  sessionExpired = true
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
  }
}

apiClient.interceptors.request.use((config) => {
  if (sessionExpired && !isAnonymousAuthRequest(config)) {
    return Promise.reject(sessionExpiredError(config))
  }
  if (!isAnonymousAuthRequest(config)) {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.isSessionExpired) {
      return Promise.reject(error)
    }
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAnonymousAuthRequest(original)
    ) {
      original._retry = true
      if (sessionExpired) {
        return Promise.reject(error)
      }
      const refresh = getRefreshToken()
      if (!refresh) {
        expireSession()
        return Promise.reject(error)
      }
      try {
        if (!refreshPromise) {
          refreshPromise = apiClient
            .post('/auth/refresh/', { refresh })
            .then((res) => {
              const payload = res.data?.data || {}
              if (!payload.access) {
                throw new Error('Refresh did not return an access token')
              }
              persistSession({
                access: payload.access,
                refresh: payload.refresh || refresh,
              })
              return payload.access
            })
            .finally(() => {
              refreshPromise = null
            })
        }
        const access = await refreshPromise
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${access}`
        return apiClient(original)
      } catch (refreshError) {
        expireSession()
        return Promise.reject(refreshError)
      }
    }
    if (error.response?.status === 401 && original && isAnonymousAuthRequest(original)) {
      if (String(original.url || '').includes('/auth/refresh/')) {
        expireSession()
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
