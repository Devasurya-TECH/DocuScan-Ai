import api from './api'

export async function login(username, password) {
  const response = await api.post('/auth/token/', { username, password })
  const { access, refresh } = response.data
  localStorage.setItem('docuscan_access', access)
  localStorage.setItem('docuscan_refresh', refresh)
  try {
    const profile = await getProfile()
    localStorage.setItem('docuscan_user', JSON.stringify(profile))
    return { tokens: response.data, user: profile }
  } catch {
    const fallbackUser = { username }
    localStorage.setItem('docuscan_user', JSON.stringify(fallbackUser))
    return { tokens: response.data, user: fallbackUser }
  }
}

export async function register(userData) {
  const response = await api.post('/auth/register/', userData)
  return response.data
}

export async function getProfile() {
  const response = await api.get('/auth/profile/')
  return response.data
}

export function logout() {
  localStorage.removeItem('docuscan_access')
  localStorage.removeItem('docuscan_refresh')
  localStorage.removeItem('docuscan_user')
}

export function getStoredUser() {
  const raw = localStorage.getItem('docuscan_user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function isAuthenticated() {
  return !!localStorage.getItem('docuscan_access')
}
