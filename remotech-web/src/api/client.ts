import axios, {
  AxiosError,
  type AxiosHeaders,
  type InternalAxiosRequestConfig,
} from 'axios'

import { ApiError, toApiError } from './errors'
import { notifyApiError } from './notify'
import { tokenStorage } from './tokenStorage'
import type { AccessTokenResponse } from '@/types/auth'

/** Dispatch ke AuthContext saat sesi benar-benar berakhir (refresh gagal). */
export const AUTH_EXPIRED_EVENT = 'remotech:auth-expired'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(
  /\/+$/,
  '',
)

/** Endpoint auth tidak boleh coba refresh saat balik 401 (hindari loop). */
const AUTH_PATHS = [
  '/token/',
  '/token/refresh/',
  '/register/',
  '/set-password/',
  '/forgot-password/',
  '/forgot-password/reset/',
]

const DEFAULT_TIMEOUT = 30_000
const UPLOAD_TIMEOUT = 120_000

export interface RequestMeta {
  /** Matikan toast error otomatis untuk request ini (komponen handle sendiri). */
  suppressErrorToast?: boolean
}

declare module 'axios' {
  interface AxiosRequestConfig {
    meta?: RequestMeta
    _retry?: boolean
  }
}

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  headers: {
    Accept: 'application/json',
  },
})

export { BASE_URL, UPLOAD_TIMEOUT }

function isAuthPath(url: string): boolean {
  return AUTH_PATHS.some((path) => url.startsWith(path))
}

function setBearer(headers: AxiosHeaders, token: string): void {
  headers.set('Authorization', `Bearer ${token}`)
}

/** Refresh access token. Memakai axios polos agar tidak kena interceptor sendiri. */
let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) {
    throw new ApiError({
      status: 401,
      type: 'client_error',
      errors: [
        { code: 'not_authenticated', detail: 'Sesi berakhir. Silakan login kembali.', attr: null },
      ],
    })
  }

  const { data } = await axios.post<AccessTokenResponse>(
    `${BASE_URL}/token/refresh/`,
    { refresh },
    { timeout: DEFAULT_TIMEOUT },
  )

  tokenStorage.setAccess(data.access)
  return data.access
}

function getRefreshedAccess(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function sessionExpiredToast(hadSession: boolean): void {
  notifyApiError(
    new ApiError({
      status: 401,
      type: 'client_error',
      errors: [
        {
          code: 'not_authenticated',
          detail: hadSession
            ? 'Sesi berakhir. Silakan login kembali.'
            : 'Silakan login terlebih dahulu.',
          attr: null,
        },
      ],
    }),
  )
}

// ---------------------------------------------------------------------------
// Interceptors
// ---------------------------------------------------------------------------

api.interceptors.request.use((config) => {
  const access = tokenStorage.getAccess()
  if (access && config.headers) {
    setBearer(config.headers, access)
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined
    const status = error.response?.status
    const suppressToast = original?.meta?.suppressErrorToast === true

    // 401 → refresh sekali (single-flight), lalu ulangi request asli.
    if (
      status === 401 &&
      original &&
      !original._retry &&
      original.url &&
      !isAuthPath(original.url) &&
      tokenStorage.getRefresh()
    ) {
      original._retry = true

      try {
        const access = await getRefreshedAccess()
        if (original.headers) {
          setBearer(original.headers as AxiosHeaders, access)
        }
        return api(original)
      } catch (refreshError) {
        const refreshApiError = toApiError(refreshError)
        // status !== null → server menolak refresh (token kedaluwarsa/tidak valid);
        // status === null → gangguan jaringan, sesi tetap dipertahankan.
        const hadSession = tokenStorage.hasSession()

        if (refreshApiError.status !== null && hadSession) {
          tokenStorage.clear()
          window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
          if (!suppressToast) {
            sessionExpiredToast(true)
          }
        } else if (!suppressToast) {
          notifyApiError(refreshApiError)
        }

        return Promise.reject(refreshApiError)
      }
    }

    const apiError = toApiError(error)
    const isAuthRequest = original?.url ? isAuthPath(original.url) : false

    if (status === 401) {
      // Endpoint auth (login dsb.): tanpa side-effect & tanpa toast —
      // kesalahan ditampilkan form itu sendiri.
      if (!isAuthRequest) {
        const hadSession = tokenStorage.hasSession()
        if (hadSession) {
          tokenStorage.clear()
          window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
        }
        if (!suppressToast) {
          sessionExpiredToast(hadSession)
        }
      }
      return Promise.reject(apiError)
    }

    if (!suppressToast) {
      notifyApiError(apiError)
    }

    return Promise.reject(apiError)
  },
)
