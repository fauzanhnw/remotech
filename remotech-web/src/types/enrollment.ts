/** Pendaftaran user ke course. */

import type { IsoDateTime } from './common'

/**
 * GET /enroll/{id}/ — enrollment hanya dibuat backend (lewat alur order /
 * pembayaran), jadi tidak ada payload create/update.
 */
export interface CourseEnrollment {
  id: number
  course: number
  user: number
  enrolled_at: IsoDateTime
}
