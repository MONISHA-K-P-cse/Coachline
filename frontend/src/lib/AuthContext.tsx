import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import * as api from './apiClient'
import { setAuthToken } from './apiClient'

const TOKEN_STORAGE_KEY = 'coachline_token'

interface AuthContextValue {
  user: api.User | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; password: string; full_name?: string }) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.getMe()
      setUser(me)
    } catch {
      setAuthToken(null)
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (stored) {
      setAuthToken(stored)
      refreshUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [refreshUser])

  const login = useCallback(async (email: string, password: string) => {
    setError(null)
    try {
      const { access_token } = await api.login(email, password)
      setAuthToken(access_token)
      localStorage.setItem(TOKEN_STORAGE_KEY, access_token)
      await refreshUser()
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : 'Login failed.')
      throw e
    }
  }, [refreshUser])

  const register = useCallback(async (data: { email: string; password: string; full_name?: string }) => {
    setError(null)
    try {
      await api.register(data)
      await login(data.email, data.password)
    } catch (e) {
      setError(e instanceof api.ApiError ? e.message : 'Registration failed.')
      throw e
    }
  }, [login])

  const logout = useCallback(() => {
    setAuthToken(null)
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
