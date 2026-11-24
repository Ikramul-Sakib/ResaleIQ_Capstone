import axios from 'axios'

// Empty in development (Vite proxy); the Flask URL in production.
export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

const TOKEN_KEY = 'resaleiq_token'

export const tokenStorage = {
  get() {
    try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
  },
  set(token) {
    try { localStorage.setItem(TOKEN_KEY, token) } catch { /* private mode */ }
  },
  clear() {
    try { localStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ }
  },
}

const api = axios.create({ baseURL: `${API_BASE}/api`, timeout: 60000 })

api.interceptors.request.use((config) => {
  const token = tokenStorage.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default api

/** A user-friendly message for any failed request. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (error?.response?.data?.error?.message) return error.response.data.error.message
  if (error?.response?.status === 413) return 'The upload is too large. Each photo must be 8 MB or smaller.'
  if (error?.request && !error.response) return 'Cannot reach the server. Make sure the backend is running.'
  return fallback
}

export function fieldErrors(error) {
  return error?.response?.data?.error?.fields || {}
}

export function imageUrl(path) {
  if (!path) return ''
  return /^https?:/.test(path) ? path : `${API_BASE}${path}`
}
