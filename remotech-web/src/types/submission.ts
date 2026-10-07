/** Pengumpulan tugas assignment oleh user. */

import type { IsoDateTime } from './common'

/** GET /submission/{id}/ — `submit_on`, `score` awal, dan timestamp diisi backend. */
export interface Submission {
  id: number
  user: number
  assignment: number
  submission_url: string
  submit_on: IsoDateTime
  score: number
  reviewed_by: string
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/**
 * POST /submission/ — `user` diisi backend dari token (body diabaikan),
 * `score`/`reviewed_by` di-reset saat create (hanya mentor via PATCH).
 */
export interface SubmissionCreate {
  user?: number
  assignment: number
  /** Tautan hasil tugas (mis. Google Drive), harus URL valid. */
  submission_url: string
  score?: number
  reviewed_by?: string
}
