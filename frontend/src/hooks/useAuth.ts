import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuthStore } from '../store/authStore'

export function useAuth() {
  const { user, accessToken, isAuthenticated, isLoading, setAuth, clearAuth, setLoading } =
    useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (accessToken && !user) {
      setLoading(true)
      authApi
        .me()
        .then((u) => setAuth(u, accessToken))
        .catch(() => clearAuth())
    }
  }, [accessToken, user, setAuth, clearAuth, setLoading])

  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true)
      const tokens = await authApi.login({ email, password })
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const user = await authApi.me(tokens.access_token)  // pass token directly — store not updated yet
      setAuth(user, tokens.access_token)
      navigate('/')
    },
    [setAuth, setLoading, navigate]
  )

  const register = useCallback(
    async (email: string, username: string, password: string) => {
      setLoading(true)
      await authApi.register({ email, username, password })
      await login(email, password)
    },
    [login, setLoading]
  )

  const logout = useCallback(async () => {
    const refresh_token = localStorage.getItem('refresh_token') ?? ''
    await authApi.logout(refresh_token).catch(() => {})
    localStorage.removeItem('refresh_token')
    clearAuth()
    navigate('/login')
  }, [clearAuth, navigate])

  return { user, isAuthenticated, isLoading, login, register, logout }
}
