import axios from 'axios'

// Configure API base URL:
// In separate frontend hosting (e.g. Vercel), set VITE_API_BASE_URL to your Render backend URL (e.g. https://docuscan-backend.onrender.com).
// In local dev or unified container deployments, it defaults to '/api'.
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || ''
const apiBase = rawBaseUrl
  ? (rawBaseUrl.endsWith('/api') || rawBaseUrl.endsWith('/api/') ? rawBaseUrl.replace(/\/$/, '') : `${rawBaseUrl.replace(/\/$/, '')}/api`)
  : '/api'

const api = axios.create({ baseURL: apiBase, timeout: 120000 })

// Request interceptor to attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('docuscan_access')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => Promise.reject(error))

// Response interceptor to attempt refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refresh = localStorage.getItem('docuscan_refresh')
      if (refresh) {
        try {
          const res = await axios.post(`${apiBase}/auth/token/refresh/`, { refresh })
          const newAccess = res.data.access
          localStorage.setItem('docuscan_access', newAccess)
          originalRequest.headers.Authorization = `Bearer ${newAccess}`
          return api(originalRequest)
        } catch {
          localStorage.removeItem('docuscan_access')
          localStorage.removeItem('docuscan_refresh')
          localStorage.removeItem('docuscan_user')
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
