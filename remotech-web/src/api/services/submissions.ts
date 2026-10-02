import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { SubmissionListParams } from '@/types/params'
import type { Submission, SubmissionCreate } from '@/types/submission'

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

/** POST /submission/ — wajib isi `user` (backend tidak auto-inject). */
export function createSubmission(payload: SubmissionCreate): Promise<Submission> {
  return postJson<Submission, SubmissionCreate>('/submission/', payload)
}

/** PATCH /submission/{id}/ — untuk review skor (`score`, `reviewed_by`). */
export function updateSubmission(
  id: number,
  payload: Partial<SubmissionCreate>,
): Promise<Submission> {
  return patchJson<Submission, Partial<SubmissionCreate>>(`/submission/${id}/`, payload)
}

/** DELETE /submission/{id}/ */
export function deleteSubmission(id: number): Promise<void> {
  return deleteJson(`/submission/${id}/`)
}
