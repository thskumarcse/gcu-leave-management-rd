const ACCESS_KEY = 'gcu.access'
const REFRESH_KEY = 'gcu.refresh'
const USER_KEY = 'gcu.user'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function readStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function persistSession({ access, refresh, user }) {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isJwtExpired(token, skewMs = 10000) {
  if (!token) return true
  const parts = token.split('.')
  if (parts.length < 2) return true
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const payload = JSON.parse(atob(padded))
    if (typeof payload.exp !== 'number') return true
    return payload.exp * 1000 <= Date.now() + skewMs
  } catch {
    return true
  }
}
