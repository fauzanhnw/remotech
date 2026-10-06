import axios from 'axios'
import { notification as fallbackNotification } from 'antd'
import type { NotificationInstance } from 'antd/es/notification/interface'

import { getFirstMessage, isApiError, toApiError } from './errors'

let notificationApi: NotificationInstance | null = null

/**
 * Pasang instance `notification` dari antd `<App>`.
 *
 * React 19: API static `notification.*` tidak dirender, jadi semua toast
 * diarahkan ke instance dari `<App>` yang dibungkus di root (pojok kanan bawah).
 */
export function registerNotificationApi(api: NotificationInstance): void {
  notificationApi = api
}

function toast(): NotificationInstance {
  return notificationApi ?? fallbackNotification
}

/**
 * Toast error global berbasis antd `notification`.
 *
 * Error validasi sengaja tidak ditampilkan di sini — serahkan ke komponen form
 * melalui `getFieldErrors()`. Non-validation error (server, jaringan, permission)
 * ditampilkan otomatis.
 */
export function notifyApiError(error: unknown): void {
  const apiError = toApiError(error)
  if (apiError.isValidationError) return
  toast().error({ message: getFirstMessage(apiError), duration: 6 })
}

/** Toast error dari `error` apa pun, atau dari teks bebas. */
export function notifyError(errorOrMessage: unknown): void {
  let text: string
  if (typeof errorOrMessage === 'string') {
    text = errorOrMessage
  } else if (
    errorOrMessage instanceof Error &&
    !isApiError(errorOrMessage) &&
    !axios.isAxiosError(errorOrMessage)
  ) {
    text = errorOrMessage.message
  } else {
    text = getFirstMessage(errorOrMessage)
  }
  toast().error({ message: text, duration: 6 })
}

export function notifySuccess(content: string): void {
  toast().success({ message: content, duration: 4 })
}

export function notifyWarning(content: string): void {
  toast().warning({ message: content, duration: 5 })
}

export function notifyInfo(content: string): void {
  toast().info({ message: content, duration: 4 })
}
