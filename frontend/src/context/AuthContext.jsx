import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuthContext } from './auth-context'
import {
  changePasswordRequest,
  fetchCurrentUser,
  loginRequest,
  logoutRequest,
} from '../services/authService'
import { resetSessionGuard, SESSION_EXPIRED_EVENT } from '../services/apiClient'
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  persistSession,
  readStoredUser,
} from '../utils/authStorage'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readStoredUser())
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function hydrate() {
      if (!getAccessToken() && !getRefreshToken()) {
        if (!cancelled) {
          setUser(null)
          setReady(true)
        }
        return
      }
      try {
        const body = await fetchCurrentUser()
        if (!cancelled) {
          const nextUser = body.data
          persistSession({ user: nextUser })
          setUser(nextUser)
        }
      } catch {
        if (!cancelled) {
          clearSession()
          setUser(null)
        }
      } finally {
        if (!cancelled) setReady(true)
      }
    }

    hydrate()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function onSessionExpired() {
      setUser(null)
      setReady(true)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired)
  }, [])

  const login = useCallback(async (empId, password) => {
    resetSessionGuard()
    const body = await loginRequest(empId, password)
    const { access, refresh, user: nextUser } = body.data
    persistSession({ access, refresh, user: nextUser })
    setUser(nextUser)
    return nextUser
  }, [])

  const changePassword = useCallback(async (payload) => {
    const body = await changePasswordRequest(payload)
    const { access, refresh, user: nextUser } = body.data
    persistSession({ access, refresh, user: nextUser })
    setUser(nextUser)
    return nextUser
  }, [])

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    await logoutRequest(refresh)
    clearSession()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const body = await fetchCurrentUser()
    persistSession({ user: body.data })
    setUser(body.data)
    return body.data
  }, [])

  const patchUser = useCallback((partial) => {
    setUser((current) => {
      if (!current) return current
      const next = { ...current, ...partial }
      persistSession({ user: next })
      return next
    })
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, logout, changePassword, refreshUser, patchUser }),
    [user, ready, login, logout, changePassword, refreshUser, patchUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
