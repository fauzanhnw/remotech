import type { AxiosRequestConfig } from 'axios'

import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { SubmissionListParams } from '@/types/params'
import type {
  Submission,
  SubmissionActionResult,
  SubmissionCreate,
} from '@/types/submission'

export type { SubmissionListParams } from '@/types/params'

/** GET /submission/ — wajib login, filter `?assignment=`, `?user=`. */
export function listSubmissions(
  params?: SubmissionListParams,
): Promise<Paginated<Submission>> {
  return getJson<Paginated<Submission>>('/submission/', { params })
}

/** GET /submission/{id}/ */
export function getSubmission(id: number): Promise<Submission> {
  return getJson<Submission>(`/submission/${id}/`)
}

/**
 * POST /submission/ — wajib isi `assignment` + `submission_url`.
 * Response menyertakan `earned_badges` (badge baru bila submit ini
 * menyelesaikan course).
 */
export function createSubmission(
  payload: SubmissionCreate,
): Promise<SubmissionActionResult> {
  return postJson<SubmissionActionResult, SubmissionCreate>(
    '/submission/',
    payload,
  )
}

/** PATCH /submission/{id}/ — untuk review skor (`score`, `reviewed_by`). */
export function updateSubmission(
  id: number,
  payload: Partial<SubmissionCreate>,
  config?: AxiosRequestConfig,
): Promise<Submission> {
  return patchJson<Submission, Partial<SubmissionCreate>>(
    `/submission/${id}/`,
    payload,
    config,
  )
}

/** DELETE /submission/{id}/ */
export function deleteSubmission(id: number): Promise<void> {
  return deleteJson(`/submission/${id}/`)
}
