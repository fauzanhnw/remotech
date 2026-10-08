import type { AxiosRequestConfig } from 'axios'

import { getJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { GradeEssayPayload, Submission } from '@/types/submission'
import type { QuizSession, UserAnswer, UserAnswerUpsert } from '@/types/quiz'

/**
 * POST /module/{id}/quiz/start/ — buka/resume quiz: membuat draft submission
 * (diadopsi bila masih kosong) + jawaban tersimpan. Wajib enroll & module
 * punya soal.
 */
export function startQuiz(moduleId: number): Promise<QuizSession> {
  return postJson<QuizSession, never>(`/module/${moduleId}/quiz/start/`)
}

/**
 * POST /module/{id}/quiz/submit/ — selesaikan quiz (sekali jalan).
 * Semua soal wajib terjawab; skor otomatis dihitung, essay ditahan
 * untuk penilaian mentor.
 */
export function submitQuiz(moduleId: number, submissionId: number): Promise<QuizSession> {
  return postJson<QuizSession, { submission: number }>(
    `/module/${moduleId}/quiz/submit/`,
    { submission: submissionId },
  )
}

/** GET /user-answer/ — filter `?submission=`, `?question=` (milik sendiri). */
export function listUserAnswers(params: {
  submission?: number
  question?: number
  page_size?: number
}): Promise<Paginated<UserAnswer>> {
  return getJson<Paginated<UserAnswer>>('/user-answer/', { params })
}

/**
 * POST /user-answer/ — simpan jawaban per soal (upsert: POST ulang
 * dengan data sama mengganti baris lama).
 */
export function upsertAnswer(
  payload: UserAnswerUpsert,
  config?: AxiosRequestConfig,
): Promise<UserAnswer> {
  return postJson<UserAnswer, UserAnswerUpsert>('/user-answer/', payload, config)
}

/**
 * POST /submission/{id}/grade-essay/ — mentor menilai seluruh jawaban essay
 * (skor pilihan dihitung ulang otomatis; total dibatasi poin module).
 */
export function gradeEssay(
  submissionId: number,
  payload: GradeEssayPayload,
  config?: AxiosRequestConfig,
): Promise<Submission> {
  return postJson<Submission, GradeEssayPayload>(
    `/submission/${submissionId}/grade-essay/`,
    payload,
    config,
  )
}
