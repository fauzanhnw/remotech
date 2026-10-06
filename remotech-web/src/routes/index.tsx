import { Route, Routes } from 'react-router-dom'

import { RequireAuth } from '@/components/RequireAuth'
import { RequireMentor } from '@/components/RequireMentor'
import { AppShell } from '@/components/layout/AppShell'
import { CoursesPage } from '@/pages/CoursesPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { MentorPage } from '@/pages/MentorPage'
import { MyAssignmentsPage } from '@/pages/MyAssignmentsPage'
import { MyCoursesPage } from '@/pages/MyCoursesPage'
import { MyOrdersPage } from '@/pages/MyOrdersPage'
import { MyPointsPage } from '@/pages/MyPointsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { RegisterPage } from '@/pages/RegisterPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="courses" element={<CoursesPage />} />

        <Route element={<RequireAuth />}>
          <Route path="my-courses" element={<MyCoursesPage />} />
          <Route path="my-assignments" element={<MyAssignmentsPage />} />
          <Route path="my-points" element={<MyPointsPage />} />
          <Route path="my-orders" element={<MyOrdersPage />} />
          <Route path="profile" element={<ProfilePage />} />

          <Route element={<RequireMentor />}>
            <Route path="mentor" element={<MentorPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="forgot-password" element={<ForgotPasswordPage />} />
    </Routes>
  )
}
