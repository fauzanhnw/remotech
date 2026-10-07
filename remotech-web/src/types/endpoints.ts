/**
 * Kontrak request/response setiap endpoint backend.
 *
 * Kunci: `"METHOD /path/"` (trailing slash wajib, sesuai DRF router).
 * Pakai bersama utility `EndpointResponse`/`EndpointBody`/`EndpointParams`
 * untuk mengambil tipe dari suatu endpoint.
 */

import type { MessageResponse, Paginated } from './api'
import type {
  AccessTokenResponse,
  ForgotPasswordPayload,
  LoginPayload,
  RefreshPayload,
  RegisterPayload,
  SetPasswordPayload,
  TokenPair,
} from './auth'
import type {
  Assignment,
  AssignmentCreate,
  ModuleContent,
  ModuleContentCreate,
} from './content'
import type {
  Course,
  CourseCreate,
  CourseModule,
  CourseModuleCreate,
} from './course'
import type { CourseEnrollment } from './enrollment'
import type { Leaderboard, LeaderboardCreate } from './leaderboard'
import type {
  CourseOrder,
  EnrollCoursePayload,
  EnrollCourseResponse,
} from './order'
import type {
  AssignmentListParams,
  CourseListParams,
  EnrollmentListParams,
  LeaderboardListParams,
  ModuleContentListParams,
  ModuleListParams,
  OrderListParams,
  ProgressListParams,
  SubmissionListParams,
} from './params'
import type {
  CourseProgressSummary,
  UserProgress,
  UserProgressCreate,
} from './progress'
import type { Submission, SubmissionCreate } from './submission'
import type { UploadResponse } from './upload'
import type { CurrentUser } from './user'

export interface ApiEndpoints {
  'GET /': { response: Record<string, string> }

  // Auth
  'POST /register/': { body: RegisterPayload; response: MessageResponse }
  'POST /set-password/': { body: SetPasswordPayload; response: MessageResponse }
  'POST /forgot-password/': { body: ForgotPasswordPayload; response: MessageResponse }
  'POST /forgot-password/reset/': { body: SetPasswordPayload; response: MessageResponse }
  'POST /token/': { body: LoginPayload; response: TokenPair }
  'POST /token/refresh/': { body: RefreshPayload; response: AccessTokenResponse }

  // Course
  'GET /course/': { params?: CourseListParams; response: Paginated<Course> }
  'POST /course/': { body: CourseCreate; response: Course }
  'GET /course/{id}/': { response: Course }
  'PATCH /course/{id}/': { body: Partial<CourseCreate>; response: Course }
  'DELETE /course/{id}/': { response: void }

  // Course module
  'GET /module/': { params?: ModuleListParams; response: Paginated<CourseModule> }
  'POST /module/': { body: CourseModuleCreate; response: CourseModule }
  'GET /module/{id}/': { response: CourseModule }
  'PATCH /module/{id}/': { body: Partial<CourseModuleCreate>; response: CourseModule }
  'DELETE /module/{id}/': { response: void }

  // Module content
  'GET /module-content/': {
    params?: ModuleContentListParams
    response: Paginated<ModuleContent>
  }
  'POST /module-content/': { body: ModuleContentCreate; response: ModuleContent }
  'GET /module-content/{id}/': { response: ModuleContent }
  'PATCH /module-content/{id}/': {
    body: Partial<ModuleContentCreate>
    response: ModuleContent
  }
  'DELETE /module-content/{id}/': { response: void }

  // Order
  'GET /order/': { params?: OrderListParams; response: Paginated<CourseOrder> }
  'GET /order/{id}/': { response: CourseOrder }
  'POST /order/enroll/': { body: EnrollCoursePayload; response: EnrollCourseResponse }
  'POST /order/{id}/check-payment/': { response: CourseOrder }

  // Assignment
  'GET /assignment/': {
    params?: AssignmentListParams
    response: Paginated<Assignment>
  }
  'POST /assignment/': { body: AssignmentCreate; response: Assignment }
  'GET /assignment/{id}/': { response: Assignment }
  'PATCH /assignment/{id}/': { body: Partial<AssignmentCreate>; response: Assignment }
  'DELETE /assignment/{id}/': { response: void }

  // Enrollment (read-only; dibuat backend lewat alur order)
  'GET /enroll/': {
    params?: EnrollmentListParams
    response: Paginated<CourseEnrollment>
  }
  'GET /enroll/{id}/': { response: CourseEnrollment }

  // Progress (ditandai selesai per module lewat halaman detail)
  'GET /progress/': { params?: ProgressListParams; response: Paginated<UserProgress> }
  'POST /progress/': { body: UserProgressCreate; response: UserProgress }
  'DELETE /progress/{id}/': { response: void }
  'GET /progress/summary/': { response: CourseProgressSummary[] }

  // Leaderboard
  'GET /leaderboard/': {
    params?: LeaderboardListParams
    response: Paginated<Leaderboard>
  }
  'POST /leaderboard/': { body: LeaderboardCreate; response: Leaderboard }
  'GET /leaderboard/{id}/': { response: Leaderboard }
  'PATCH /leaderboard/{id}/': { body: Partial<LeaderboardCreate>; response: Leaderboard }
  'DELETE /leaderboard/{id}/': { response: void }

  // Submission
  'GET /submission/': {
    params?: SubmissionListParams
    response: Paginated<Submission>
  }
  'POST /submission/': { body: SubmissionCreate; response: Submission }
  'GET /submission/{id}/': { response: Submission }
  'PATCH /submission/{id}/': { body: Partial<SubmissionCreate>; response: Submission }
  'DELETE /submission/{id}/': { response: void }

  // Upload
  'POST /upload/image/': { body: FormData; response: UploadResponse }
  'POST /upload/document/': { body: FormData; response: UploadResponse }

  // User
  'GET /user/me/': { response: CurrentUser }
}

/** Tipe response dari sebuah endpoint. */
export type EndpointResponse<K extends keyof ApiEndpoints> =
  ApiEndpoints[K] extends { response: infer R } ? R : never

/** Tipe body request dari sebuah endpoint (tanpa body → `never`). */
export type EndpointBody<K extends keyof ApiEndpoints> =
  ApiEndpoints[K] extends { body: infer B } ? B : never

/** Tipe query params dari sebuah endpoint (tanpa params → `never`). */
export type EndpointParams<K extends keyof ApiEndpoints> =
  ApiEndpoints[K] extends { params?: infer P } ? P : never
