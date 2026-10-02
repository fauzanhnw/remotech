/** Pendaftaran user ke course. */

import type { IsoDateTime } from './common'

/** GET /enroll/{id}/ */
export interface CourseEnrollment {
  id: number
  course: number
  user: number
  enrolled_at: IsoDateTime
}

/** POST /enroll/ — backend tidak auto-inject user. */
export interface CourseEnrollmentCreate {
  course: number
  user: number
}
