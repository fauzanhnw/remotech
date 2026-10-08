/** Pengumpulan tugas (assignment) dan hasil quiz. */

import type { IsoDateTime } from './common'

/**
 * GET /submission/{id}/ — tugas (punya `assignment`) atau hasil quiz
 * (tanpa `assignment`). `module`/`module_title`/`max_score`/
 * `course`/`course_title` adalah field turunan backend; `module` null untuk
 * draft quiz yang belum dijawab.
 */
export interface Submission {
  id: number
  user: number
  /** Nama lengkap (fallback username) pemilik submission. */
  user_name: string
  assignment: number | null
  module: number | null
  module_title: string
  /** Course pemilik module; null bila belum bisa diturunkan. */
  course: number | null
  /** Judul course pemilik module. */
  course_title: string
  /** Poin maksimal module; null bila belum bisa diturunkan. */
  max_score: number | null
  is_quiz: boolean
  /** true = sudah final (tugas dinilai mentor / quiz tanpa essay dinilai system). */
  is_graded: boolean
  submission_url: string
  submit_on: IsoDateTime
  score: number
  /** "" = tugas belum dinilai / quiz essay menunggu; "system"/username mentor. */
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

/** POST /submission/{id}/grade-essay/ — nilai tiap jawaban essay (mentor). */
export interface GradeEssayPayload {
  answers: { id: number; score: number }[]
}
