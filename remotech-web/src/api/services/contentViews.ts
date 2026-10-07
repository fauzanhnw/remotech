import type { AxiosRequestConfig } from 'axios'

import { getJson, postJson } from './shared'
import type { ContentViewMarkResult, ContentViewedList } from '@/types/contentView'

/**
 * POST /content-view/{id}/ — tandai konten sudah dibuka (idempoten).
 * Module text/video baru otomatis `finish` (di backend) setelah seluruh
 * kontennya dilihat; upload/quiz tidak pernah auto-finish lewat sini.
 * Pakai `config.meta.suppressErrorToast` untuk panggilan otomatis.
 */
export function markContentViewed(
  contentId: number,
  config?: AxiosRequestConfig,
): Promise<ContentViewMarkResult> {
  return postJson<ContentViewMarkResult>(`/content-view/${contentId}/`, undefined, config)
}

/** GET /content-view/?course= — id konten sudah-dibuka milik sendiri. */
export function listContentViewed(params: { course: number }): Promise<ContentViewedList> {
  return getJson<ContentViewedList>('/content-view/', { params })
}
