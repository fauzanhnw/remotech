/** Query parameter list/filter per endpoint (sesuai filterset_fields backend). */

import type { PaginationParams } from './api'
import type { BadgeRuleType } from './badge'
import type { OrderStatus } from './order'

/**
 * GET /course/ — filter `?is_open=`, `?is_publish=`,
 * `?price__lte=` / `?price__gt=`, search `?search=`, sort `?ordering=`
 * (`created_at` | `price` | `title`, default `-created_at`).
 */
export interface CourseListParams extends PaginationParams {
  is_open?: boolean
  is_publish?: boolean
  price__lte?: number
  price__gt?: number
  search?: string
  ordering?: 'created_at' | '-created_at' | 'price' | '-price' | 'title' | '-title'
}

/** GET /module/ — filter `?course=`. */
export interface ModuleListParams extends PaginationParams {
  course?: number
}

/** GET /module-content/ — filter `?module=`. */
export interface ModuleContentListParams extends PaginationParams {
  module?: number
}

/** GET /question/ — filter `?module=` (hanya module quiz). */
export interface QuestionListParams extends PaginationParams {
  module?: number
}

/** GET /order/ — filter `?course=`, `?user=`, `?transaction_status=`. */
export interface OrderListParams extends PaginationParams {
  course?: number
  user?: number
  transaction_status?: OrderStatus
}

/**
 * GET /enroll/ — filter `?course=`, `?user=`, search `?search=` (judul course),
 * sort `?ordering=enrolled_at` (default `-enrolled_at`).
 */
export interface EnrollmentListParams extends PaginationParams {
  course?: number
  user?: number
  search?: string
  ordering?: 'enrolled_at' | '-enrolled_at'
}

/** GET /progress/ — filter `?course=` (hanya progres milik sendiri). */
export interface ProgressListParams extends PaginationParams {
  course?: number
}

/** GET /assignment/ — filter `?course_module=`. */
export interface AssignmentListParams extends PaginationParams {
  course_module?: number
}

/** GET /leaderboard/ — filter `?course=`, `?user=`. */
export interface LeaderboardListParams extends PaginationParams {
  course?: number
  user?: number
}

/**
 * GET /submission/ — filter `?assignment=`, `?user=`, `?module=`
 * (tugas dari assignment ataupun hasil quiz), `?graded=true|false`.
 */
export interface SubmissionListParams extends PaginationParams {
  assignment?: number
  user?: number
  module?: number
  graded?: boolean
}

/** GET /badge/ — filter `?course=`, `?rule_type=`. */
export interface BadgeListParams extends PaginationParams {
  course?: number
  rule_type?: BadgeRuleType
}

/** GET /user-badge/ — filter `?badge=`, `?user=`, `?badge__course=`. */
export interface UserBadgeListParams extends PaginationParams {
  badge?: number
  user?: number
  badge__course?: number
}

/** GET /point-bonus/ — filter `?course=`, `?user=` (hanya pemilik course). */
export interface PointBonusListParams extends PaginationParams {
  course?: number
  user?: number
}
