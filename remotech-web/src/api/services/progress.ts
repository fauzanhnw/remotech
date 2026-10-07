import type { AxiosRequestConfig } from 'axios'

import { deleteJson, getJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { ProgressListParams } from '@/types/params'
import type { CourseProgressSummary, UserProgress, UserProgressCreate } from '@/types/progress'

export type { ProgressListParams } from '@/types/params'

/**
 * GET /progress/ — wajib login, hanya progres milik sendiri.
 * Filter `?course=`.
 */
export function listProgress(params?: ProgressListParams): Promise<Paginated<UserProgress>> {
  return getJson<Paginated<UserProgress>>('/progress/', { params })
}

/**
 * POST /progress/ — tandai module selesai (idempotent, status selalu `finish`).
 * Wajib ter-enroll di course module tersebut.
 * Pakai `config.meta.suppressErrorToast` untuk aksi otomatis (tanpa toast).
 */
export function markModuleComplete(
  module: number,
  config?: AxiosRequestConfig,
): Promise<UserProgress> {
  return postJson<UserProgress, UserProgressCreate>('/progress/', { module }, config)
}

/** DELETE /progress/{id}/ — batalkan tanda selesai (204 tanpa body). */
export function unmarkProgress(id: number): Promise<void> {
  return deleteJson(`/progress/${id}/`)
}

/** GET /progress/summary/ — ringkasan semua course yang di-enroll (tanpa paginasi). */
export function getProgressSummary(): Promise<CourseProgressSummary[]> {
  return getJson<CourseProgressSummary[]>('/progress/summary/')
}
