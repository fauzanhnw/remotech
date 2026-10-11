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
import type { Badge, BadgeCreate, MyBadgeEntry, UserBadge, UserBadgeAwardPayload } from './badge'
import type {
  Assignment,
  AssignmentCreate,
  ModuleContent,
  ModuleContentCreate,
} from './content'
import type { ContentViewMarkResult, ContentViewedList } from './contentView'
import type {
  Course,
  CourseCreate,
  CourseModule,
  CourseModuleCreate,
} from './course'
import type { CourseEnrollment } from './enrollment'
import type {
  Leaderboard,
  LeaderboardCreate,
  LeaderboardDetailEntry,
  MyLeaderboard,
} from './leaderboard'
import type {
  CourseOrder,
  EnrollCoursePayload,
  EnrollCourseResponse,
} from './order'
import type {
  AssignmentListParams,
  BadgeListParams,
  CourseListParams,
  EnrollmentListParams,
  LeaderboardListParams,
  ModuleContentListParams,
  ModuleListParams,
  OrderListParams,
  ProgressListParams,
  QuestionListParams,
  SubmissionListParams,
  UserBadgeListParams,
} from './params'
import type {
  CourseProgressSummary,
  UserProgress,
  UserProgressCreate,
  UserProgressCreateResult,
  WeeklyActivity,
} from './progress'
import type {
  GradeEssayPayload,
  Submission,
  SubmissionActionResult,
  SubmissionCreate,
} from './submission'
import type {
  Question,
  QuestionCreate,
  QuizSession,
  UserAnswer,
  UserAnswerUpsert,
} from './quiz'
import type { UploadResponse } from './upload'
import type {
  ChangePasswordPayload,
  CurrentUser,
  ProfileUpdatePayload,
} from './user'

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
  'POST /progress/': { body: UserProgressCreate; response: UserProgressCreateResult }
  'DELETE /progress/{id}/': { response: void }
  'GET /progress/summary/': { response: CourseProgressSummary[] }
  'GET /progress/activity/': { response: WeeklyActivity }

  // Content view (konten dibuka — syarat auto-complete module text/video)
  'GET /content-view/': { params?: { course?: number }; response: ContentViewedList }
  'POST /content-view/{id}/': { response: ContentViewMarkResult }

  // Leaderboard
  'GET /leaderboard/': {
    params?: LeaderboardListParams
    response: Paginated<Leaderboard>
  }
  'POST /leaderboard/': { body: LeaderboardCreate; response: Leaderboard }
  'GET /leaderboard/{id}/': { response: Leaderboard }
  'GET /leaderboard/{id}/details/': { response: LeaderboardDetailEntry[] }
  'GET /leaderboard/me/': { response: MyLeaderboard }
  'PATCH /leaderboard/{id}/': { body: Partial<LeaderboardCreate>; response: Leaderboard }
  'DELETE /leaderboard/{id}/': { response: void }

  // Submission
  'GET /submission/': {
    params?: SubmissionListParams
    response: Paginated<Submission>
  }
  'POST /submission/': { body: SubmissionCreate; response: SubmissionActionResult }
  'GET /submission/{id}/': { response: Submission }
  'PATCH /submission/{id}/': { body: Partial<SubmissionCreate>; response: Submission }
  'DELETE /submission/{id}/': { response: void }
  // Penilaian bagian essay quiz (mentor) — total dibatasi poin module.
  'POST /submission/{id}/grade-essay/': {
    body: GradeEssayPayload
    response: SubmissionActionResult
  }

  // Question (soal quiz — hanya module berkategori quiz)
  'GET /question/': { params?: QuestionListParams; response: Paginated<Question> }
  'POST /question/': { body: QuestionCreate; response: Question }
  'GET /question/{id}/': { response: Question }
  'PATCH /question/{id}/': { body: Partial<QuestionCreate>; response: Question }
  'DELETE /question/{id}/': { response: void }

  // User answer (jawaban per soal — upsert per submission + soal)
  'GET /user-answer/': {
    params?: { submission?: number; question?: number }
    response: Paginated<UserAnswer>
  }
  'POST /user-answer/': { body: UserAnswerUpsert; response: UserAnswer }
  'DELETE /user-answer/{id}/': { response: void }

  // Badge (definisi per course — tulis hanya pemilik course)
  'GET /badge/': { params?: BadgeListParams; response: Paginated<Badge> }
  'POST /badge/': { body: BadgeCreate | FormData; response: Badge }
  'GET /badge/{id}/': { response: Badge }
  'PATCH /badge/{id}/': { body: Partial<BadgeCreate> | FormData; response: Badge }
  'DELETE /badge/{id}/': { response: void }

  // User badge (kepemilikan: otomatis via sync / manual mentor)
  'GET /user-badge/': {
    params?: UserBadgeListParams
    response: Paginated<UserBadge>
  }
  'POST /user-badge/': { body: UserBadgeAwardPayload; response: UserBadge }
  'GET /user-badge/{id}/': { response: UserBadge }
  'DELETE /user-badge/{id}/': { response: void }
  'GET /user-badge/me/': { params?: { course?: number }; response: MyBadgeEntry[] }

  // Quiz flow (student): buka/resume → jawab → submit
  'POST /module/{id}/quiz/start/': { body?: never; response: QuizSession }
  'POST /module/{id}/quiz/submit/': { body: { submission: number }; response: QuizSession }

  // Upload
  'POST /upload/image/': { body: FormData; response: UploadResponse }
  'POST /upload/document/': { body: FormData; response: UploadResponse }

  // User
  'GET /user/me/': { response: CurrentUser }
  'PATCH /user/me/': { body: ProfileUpdatePayload; response: CurrentUser }
  'POST /user/change-password/': {
    body: ChangePasswordPayload
    response: MessageResponse
  }
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
