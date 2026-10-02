import { message } from 'antd'

import { getFirstMessage, toApiError } from './errors'

/**
 * Toast error global berbasis antd `message`.
 *
 * Error validasi sengaja tidak ditampilkan di sini — serahkan ke komponen form
 * melalui `getFieldErrors()`. Non-validation error (server, jaringan, permission)
 * ditampilkan otomatis.
 */
export function notifyApiError(error: unknown): void {
  const apiError = toApiError(error)
  if (apiError.isValidationError) return
  message.error(getFirstMessage(apiError))
}

export function notifySuccess(content: string): void {
  message.success(content)
}

export function notifyInfo(content: string): void {
  message.info(content)
}
