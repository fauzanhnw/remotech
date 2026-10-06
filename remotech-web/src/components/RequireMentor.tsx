import { Spin } from 'antd'
import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { ForbiddenPage } from '@/pages/ForbiddenPage'

/** Guard rute khusus mentor — butuh login, profil terisi, dan role `mentor`. */
export function RequireMentor() {
  const { isAuthenticated, profileLoaded, user } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Profil belum selesai dimuat — tahan dulu agar mentor tidak kedip 403.
  if (!profileLoaded) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Spin size="large" />
      </div>
    )
  }

  if (!user?.is_mentor) {
    return <ForbiddenPage />
  }

  return <Outlet />
}
