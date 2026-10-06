import { createContext, useContext } from 'react'

import type { CurrentUser } from '@/types/user'

export interface AuthValue {
  /** Profil user login; `null` bila belum login atau profil gagal dimuat. */
  user: CurrentUser | null
  /** True bila ada sesi token (belum tentu profil sudah terisi). */
  isAuthenticated: boolean
  /** True bila profil dari GET /user/me/ sudah selesai dimuat (sukses maupun gagal). */
  profileLoaded: boolean
  /** Login dengan email + password, lalu muat profil. Tolak bila login gagal. */
  login: (username: string, password: string) => Promise<void>
  /** Buang token di sisi client lalu reset state. */
  logout: () => void
  /** Muat ulang profil dari GET /user/me/. */
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>.')
  }
  return context
}
