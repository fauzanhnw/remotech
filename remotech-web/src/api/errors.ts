import axios from 'axios'

import type { ApiErrorItem, ApiErrorResponse, ApiErrorType } from '@/types/api'

interface ApiErrorInit {
  status: number | null
  type: ApiErrorType | null
  errors: ApiErrorItem[]
}

/**
 * Error ternormalisasi dari semua panggilan API.
 *
 * - `status` `null` berarti request tidak sampai ke server (network/timeout).
 * - `type` mengikuti envelope drf-standardized-errors; `null` untuk error non-HTTP.
 */
export class ApiError extends Error {
  readonly status: number | null
  readonly type: ApiErrorType | null
  readonly errors: ApiErrorItem[]

  constructor({ status, type, errors }: ApiErrorInit) {
    super(errors[0]?.detail ?? 'An unknown error occurred.')
    this.name = 'ApiError'
    this.status = status
    this.type = type
    this.errors = errors
  }

  get isNetworkError(): boolean {
    return this.status === null
  }

  get isValidationError(): boolean {
    return this.type === 'validation_error'
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

/**
 * Field error per nama field, untuk ditampilkan di form.
 * Hanya berisi error validasi yang punya `attr`.
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  const apiError = toApiError(error)
  const fieldErrors: Record<string, string> = {}

  for (const item of apiError.errors) {
    if (item.attr && !(item.attr in fieldErrors)) {
      fieldErrors[item.attr] = item.detail
    }
  }

  return fieldErrors
}

/** Pesan pertama yang human-readable, cocok untuk toast. */
export function getFirstMessage(error: unknown): string {
  return toApiError(error).errors[0]?.detail ?? 'An unknown error occurred.'
}

function isApiErrorResponse(data: unknown): data is ApiErrorResponse {
  if (!data || typeof data !== 'object') return false
  const candidate = data as Partial<ApiErrorResponse>
  return (
    typeof candidate.type === 'string' &&
    Array.isArray(candidate.errors) &&
    candidate.errors.length > 0
  )
}

function normalizeItems(items: ApiErrorItem[]): ApiErrorItem[] {
  return items.map((item) => ({
    code: typeof item.code === 'string' ? item.code : 'unknown_error',
    detail: typeof item.detail === 'string' ? item.detail : String(item.detail ?? ''),
    attr: typeof item.attr === 'string' ? item.attr : null,
  }))
}

function httpError(status: number, detail: string): ApiError {
  return new ApiError({
    status,
    type: status >= 500 ? 'server_error' : 'client_error',
    errors: [{ code: 'unknown_error', detail, attr: null }],
  })
}

/**
 * Ubah segala bentuk error (AxiosError, ApiError, error biasa) menjadi `ApiError`.
 * Menangani: envelope drf-standardized-errors, body non-JSON (HTML debug Django),
 * timeout, dan gangguan jaringan.
 */
export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) return error

  if (axios.isAxiosError(error)) {
    const response = error.response

    if (response) {
      const data = response.data

      if (isApiErrorResponse(data)) {
        return new ApiError({
          status: response.status,
          type: data.type,
          errors: normalizeItems(data.errors),
        })
      }

      // Body non-standar: DRF lama ({detail}), HTML debug Django, plain text.
      if (data && typeof data === 'object' && 'detail' in data) {
        const detail = (data as { detail: unknown }).detail
        if (typeof detail === 'string') {
          return new ApiError({
            status: response.status,
            type: response.status >= 500 ? 'server_error' : 'client_error',
            errors: [{ code: 'unknown_error', detail, attr: null }],
          })
        }
      }

      return httpError(
        response.status,
        response.status >= 500
          ? 'Terjadi kesalahan pada server. Coba lagi nanti.'
          : `Permintaan gagal (HTTP ${response.status}).`,
      )
    }

    const timedOut = error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT'
    return new ApiError({
      status: null,
      type: null,
      errors: [
        {
          code: timedOut ? 'timeout' : 'network_error',
          detail: timedOut
            ? 'The request timed out. Please try again.'
            : 'Could not connect to the server. Please check your connection.',
          attr: null,
        },
      ],
    })
  }

  return new ApiError({
    status: null,
    type: null,
    errors: [
      {
        code: 'unknown_error',
        detail: 'An unknown error occurred.',
        attr: null,
      },
    ],
  })
}
