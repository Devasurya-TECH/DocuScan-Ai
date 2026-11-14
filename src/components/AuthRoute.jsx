import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Inverse guard — prevents already-authenticated users from reaching
 * /login and /register. Redirects them to the dashboard instead.
 */
export default function AuthRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
      </div>
    )
  }

  if (isAuthenticated) {
    // Respect any ?next= param that was embedded in the auth URL
    const params = new URLSearchParams(location.search)
    const next = params.get('next')
    return <Navigate to={next || '/dashboard'} replace />
  }

  return children
}
