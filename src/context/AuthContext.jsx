import { createContext, useContext, useEffect, useState } from 'react'
import * as authService from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => authService.getStoredUser())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const handleExpired = () => setUser(null)
    window.addEventListener('docuscan_session_expired', handleExpired)
    return () => window.removeEventListener('docuscan_session_expired', handleExpired)
  }, [])

  useEffect(() => {
    if (authService.isAuthenticated()) {
      authService.getProfile()
        .then((profile) => {
          setUser(profile)
          localStorage.setItem('docuscan_user', JSON.stringify(profile))
        })
        .catch(() => {
          // Keep stored user if network hiccup
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username, password) => {
    const res = await authService.login(username, password)
    setUser(res.user)
    return res
  }

  const register = async (userData) => {
    const res = await authService.register(userData)
    return res
  }

  const logout = () => {
    authService.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
