/** Tipe error terstandardisasi dari backend (drf-standardized-errors). */

export type ApiErrorType = 'validation_error' | 'client_error' | 'server_error'

export interface ApiErrorItem {
  /** Kode machine-readable, mis. "required", "not_found", "token_not_valid". */
  code: string
  /** Pesan human-readable dari backend. */
  detail: string
  /** Nama field yang error (validation error saja), `null` untuk error non-field. */
  attr: string | null
}

export interface ApiErrorResponse {
  type: ApiErrorType
  errors: ApiErrorItem[]
}

/** Envelope pagination standar DRF (PageNumberPagination). */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PaginationParams {
  page?: number
  /** Maksimal 100 (dibatasi backend). */
  page_size?: number
}

/** Respons message-only dari backend (register, reset password, dll.). */
export interface MessageResponse {
  message: string
}
