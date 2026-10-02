import type { TokenPair } from '@/types/auth'

const ACCESS_TOKEN_KEY = 'remotech_access_token'
const REFRESH_TOKEN_KEY = 'remotech_refresh_token'

function read(key: string): string | null {
  return localStorage.getItem(key)
}

function write(key: string, value: string): void {
  localStorage.setItem(key, value)
}

function remove(key: string): void {
  localStorage.removeItem(key)
}

/** Penyimpanan token JWT di localStorage (access 30 menit, refresh 7 hari). */
export const tokenStorage = {
  getAccess(): string | null {
    return read(ACCESS_TOKEN_KEY)
  },

  getRefresh(): string | null {
    return read(REFRESH_TOKEN_KEY)
  },

  setPair({ access, refresh }: TokenPair): void {
    write(ACCESS_TOKEN_KEY, access)
    write(REFRESH_TOKEN_KEY, refresh)
  },

  setAccess(access: string): void {
    write(ACCESS_TOKEN_KEY, access)
  },

  clear(): void {
    remove(ACCESS_TOKEN_KEY)
    remove(REFRESH_TOKEN_KEY)
  },

  hasSession(): boolean {
    return Boolean(read(ACCESS_TOKEN_KEY) || read(REFRESH_TOKEN_KEY))
  },
}
