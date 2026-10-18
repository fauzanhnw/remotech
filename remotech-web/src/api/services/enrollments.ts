import { getJson } from './shared'
import type { Paginated } from '@/types/api'
import type { CourseEnrollment } from '@/types/enrollment'
import type { EnrollmentListParams } from '@/types/params'

export type { EnrollmentListParams } from '@/types/params'

/**
 * GET /enroll/ — wajib login, default hanya enrollment milik sendiri.
 * Filter `?course=`, `?user=`. `?course=` hanya melebarkan scope untuk
 * pemilik course / superuser (pemilihan student saat beri badge/poin).
 */
export function listEnrollments(
  params?: EnrollmentListParams,
): Promise<Paginated<CourseEnrollment>> {
  return getJson<Paginated<CourseEnrollment>>('/enroll/', { params })
}

/** GET /enroll/{id}/ — hanya enrollment milik sendiri. */
export function getEnrollment(id: number): Promise<CourseEnrollment> {
  return getJson<CourseEnrollment>(`/enroll/${id}/`)
}
