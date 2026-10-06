/** Query parameter list/filter per endpoint (sesuai filterset_fields backend). */

import type { PaginationParams } from './api'
import type { OrderStatus } from './order'

/** GET /course/ — filter `?is_open=`. */
export interface CourseListParams extends PaginationParams {
  is_open?: boolean
}

/** GET /module/ — filter `?course=`. */
export interface ModuleListParams extends PaginationParams {
  course?: number
}

/** GET /module-content/ — filter `?module=`. */
export interface ModuleContentListParams extends PaginationParams {
  module?: number
}

/** GET /order/ — filter `?course=`, `?user=`, `?transaction_status=`. */
export interface OrderListParams extends PaginationParams {
  course?: number
  user?: number
  transaction_status?: OrderStatus
}

/** GET /enroll/ — filter `?course=`, `?user=`. */
export interface EnrollmentListParams extends PaginationParams {
  course?: number
  user?: number
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

/** GET /submission/ — filter `?assignment=`, `?user=`. */
export interface SubmissionListParams extends PaginationParams {
  assignment?: number
  user?: number
}
