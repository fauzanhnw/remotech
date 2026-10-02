import { UPLOAD_TIMEOUT, api } from '../client'
import type { UploadResponse } from '@/types/upload'

/** POST /upload/image/ — field `image`, dikonversi backend ke webp (≤10 MB). */
export async function uploadImage(image: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('image', image)

  const response = await api.post<UploadResponse>('/upload/image/', formData, {
    timeout: UPLOAD_TIMEOUT,
  })
  return response.data
}

/** POST /upload/document/ — field `file`, maks 20 MB, tipe terbatas (pdf/doc/dll). */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post<UploadResponse>('/upload/document/', formData, {
    timeout: UPLOAD_TIMEOUT,
  })
  return response.data
}
