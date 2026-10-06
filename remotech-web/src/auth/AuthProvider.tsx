import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  AUTH_EXPIRED_EVENT,
  getMe,
  login as authLogin,
  logout as authLogout,
  tokenStorage,
} from '@/api'

import { AuthContext, type AuthValue } from './AuthContext'
import type { CurrentUser } from '@/types/user'

/** Prefix key localStorage milik tokenStorage (lihat api/tokenStorage.ts). */
const TOKEN_KEY_PREFIX = 'remotech_'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [hasSession, setHasSession] = useState(() => tokenStorage.hasSession())
  const [user, setUser] = useState<CurrentUser | null>(null)
  // Tanpa sesi tidak ada profil yang ditunggu, jadi dianggap sudah selesai.
  const [profileLoaded, setProfileLoaded] = useState(() => !tokenStorage.hasSession())

  const refreshUser = useCallback(async () => {
    try {
      setUser(await getMe())
    } catch {
      // Profil gagal dimuat tidak menghapus sesi; biarkan UI pakai fallback.
      setUser(null)
    } finally {
      setProfileLoaded(true)
    }
  }, [])

  // Hydrate profil saat aplikasi dibuka dengan sesi yang masih ada.
  useEffect(() => {
    if (!tokenStorage.hasSession()) return

    let cancelled = false
    getMe()
      .then((profile) => {
        if (!cancelled) setUser(profile)
      })
      .catch(() => {
        // Profil gagal dimuat tidak menghapus sesi; biarkan UI pakai fallback.
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setProfileLoaded(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Sesi berakhir (refresh token gagal) atau perubahan token di tab lain.
  useEffect(() => {
    const onExpired = () => {
      setHasSession(false)
      setUser(null)
    }

    const onStorage = (event: StorageEvent) => {
      if (event.key !== null && !event.key.startsWith(TOKEN_KEY_PREFIX)) return
      const hasSession = tokenStorage.hasSession()
      setHasSession(hasSession)
      if (hasSession) {
        void refreshUser()
      } else {
        setUser(null)
      }
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
      window.removeEventListener('storage', onStorage)
    }
  }, [refreshUser])

  const login = useCallback(
    async (username: string, password: string) => {
      await authLogin({ username, password })
      setHasSession(true)
      setProfileLoaded(false)
      await refreshUser()
    },
    [refreshUser],
  )

  const logout = useCallback(() => {
    authLogout()
    setHasSession(false)
    setUser(null)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({ user, isAuthenticated: hasSession, profileLoaded, login, logout, refreshUser }),
    [user, hasSession, profileLoaded, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
