/** Pendaftaran user ke course. */

import type { Course } from './course'
import type { IsoDateTime } from './common'

/**
 * GET /enroll/{id}/ — enrollment hanya dibuat backend (lewat alur order /
 * pembayaran), jadi tidak ada payload create/update. `course` berupa objek
 * course lengkap (nested serializer).
 */
export interface CourseEnrollment {
  id: number
  course: Course
  user: number
  enrolled_at: IsoDateTime
}
