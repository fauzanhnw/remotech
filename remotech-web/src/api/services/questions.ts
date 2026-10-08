import type { AxiosRequestConfig } from 'axios'

import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { QuestionListParams } from '@/types/params'
import type { Question, QuestionCreate } from '@/types/quiz'

export type { QuestionListParams } from '@/types/params'

/** GET /question/ — login, filter `?module=`. Kunci jawaban hanya untuk mentor. */
export function listQuestions(
  params?: QuestionListParams,
  config?: AxiosRequestConfig,
): Promise<Paginated<Question>> {
  return getJson<Paginated<Question>>('/question/', { ...config, params })
}

/** GET /question/{id}/ */
export function getQuestion(id: number): Promise<Question> {
  return getJson<Question>(`/question/${id}/`)
}

/**
 * POST /question/ — wajib pemilik course; `options` ditulis ulang sekaligus.
 * Gagal (400) bila module sudah ada pengerjaan.
 */
export function createQuestion(
  payload: QuestionCreate,
  config?: AxiosRequestConfig,
): Promise<Question> {
  return postJson<Question, QuestionCreate>('/question/', payload, config)
}

/** PATCH /question/{id}/ — wajib pemilik course; dikunci bila sudah ada pengerjaan. */
export function updateQuestion(
  id: number,
  payload: Partial<QuestionCreate>,
  config?: AxiosRequestConfig,
): Promise<Question> {
  return patchJson<Question, Partial<QuestionCreate>>(
    `/question/${id}/`,
    payload,
    config,
  )
}

/** DELETE /question/{id}/ — ditolak (400) bila soal sudah pernah dijawab. */
export function deleteQuestion(id: number, config?: AxiosRequestConfig): Promise<void> {
  return deleteJson(`/question/${id}/`, config)
}
