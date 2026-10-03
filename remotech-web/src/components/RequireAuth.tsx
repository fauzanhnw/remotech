import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'

/** Guard rute butuh login — selain itu lepas ke halaman login. */
export function RequireAuth() {
  const { isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
