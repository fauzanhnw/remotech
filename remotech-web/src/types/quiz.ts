/** Soal, opsi, dan jawaban quiz (module berkategori `quiz`). */

import type { IsoDateTime } from './common'
import type { Badge } from './badge'
import type { Submission } from './submission'

export type QuestionType = 'choices' | 'boolean' | 'essai'

/**
 * GET /question/{id}/ — `is_correct` hanya ikut dikirim untuk pemilik course
 * (mentor) atau saat hasil quiz sudah final; `question` adalah id soal induk.
 */
export interface QuestionOption {
  id: number
  question: number
  option_text: string
  is_correct?: boolean
  sequence: number | null
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/**
 * GET /question/{id}/ — `explanation` dikosongkan untuk student sampai
 * hasil final; `options` kosong untuk soal essay.
 */
export interface Question {
  id: number
  module: number
  question_text: string
  question_type: QuestionType
  explanation: string
  sequence: number | null
  options: QuestionOption[]
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/**
 * POST /question/ — nested `options` ditulis/terhapus sekaligus.
 * Soal essay wajib `options: []`; pilihan/boolean wajib ≥2 opsi dengan
 * tepat satu `is_correct`.
 */
export interface QuestionCreate {
  module: number
  question_text: string
  question_type: QuestionType
  explanation?: string
  sequence?: number | null
  options?: { option_text: string; is_correct?: boolean }[]
}

/**
 * GET /user-answer/ — jawaban satu user pada satu submission.
 * `score` hanya untuk soal essay (null sampai mentor menilai);
 * `is_correct` null untuk essay.
 */
export interface UserAnswer {
  id: number
  submission: number
  question: number
  question_option: number | null
  answer_text: string
  score: number | null
  is_correct: boolean | null
}

/**
 * POST /user-answer/ — upsert per (submission, soal): POST ulang dengan
 * data sama mengganti baris lama, bukan error.
 */
export interface UserAnswerUpsert {
  submission: number
  question: number
  question_option?: number
  answer_text?: string
}

/**
 * Hasil quiz (ada di response `quiz/submit/`, dan `quiz/start/` bila sudah
 * selesai). `pending` = bagian essay masih menunggu penilaian mentor.
 */
export interface QuizResult {
  score: number
  max_score: number
  auto_score: number
  auto_max: number
  essay_max: number
  correct: number
  auto_total: number
  essay_count: number
  pending: boolean
}

/** Response POST /module/{id}/quiz/start/ dan /module/{id}/quiz/submit/. */
export interface QuizSession {
  submission: Submission
  questions: Question[]
  answers: UserAnswer[]
  completed: boolean
  result?: QuizResult
  /** Badge baru yang didapat saat submit (tidak dikirim saat start). */
  earned_badges?: Badge[]
}
