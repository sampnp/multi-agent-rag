import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import type { TokenResponse, User } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    api.post<User>('/api/auth/register', data).then((r) => r.data),

  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>('/api/auth/login', data).then((r) => r.data),

  refresh: (refresh_token: string) =>
    api.post<TokenResponse>('/api/auth/refresh', { refresh_token }).then((r) => r.data),

  logout: (refresh_token: string) =>
    api.post('/api/auth/logout', { refresh_token }),

  me: (token?: string) =>
    api
      .get<User>('/api/auth/me', token ? { headers: { Authorization: `Bearer ${token}` } } : undefined)
      .then((r) => r.data),
}

export default api
