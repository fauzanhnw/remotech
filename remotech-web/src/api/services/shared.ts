import type { AxiosRequestConfig } from 'axios'

import { api } from '../client'

/** GET dan langsung kembalikan body (bukan AxiosResponse). */
export async function getJson<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await api.get<T>(url, config)
  return response.data
}

export async function postJson<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await api.post<T>(url, body, config)
  return response.data
}

export async function patchJson<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await api.patch<T>(url, body, config)
  return response.data
}

export async function putJson<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await api.put<T>(url, body, config)
  return response.data
}

/** DELETE — backend membalas 204 tanpa body. */
export async function deleteJson(url: string, config?: AxiosRequestConfig): Promise<void> {
  await api.delete(url, config)
}

/**
 * Ubah objek payload menjadi FormData (untuk endpoint multipart seperti
 * create/update course dengan thumbnail). Nilai `undefined`/`null` dibuang,
 * boolean ditulis huruf kecil agar diterima DRF.
 */
export function toFormData(data: Record<string, unknown>): FormData {
  const formData = new FormData()

  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null) continue

    if (value instanceof File) {
      formData.append(key, value)
    } else if (typeof value === 'boolean') {
      formData.append(key, value ? 'true' : 'false')
    } else {
      formData.append(key, String(value))
    }
  }

  return formData
}
