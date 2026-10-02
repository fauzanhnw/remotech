import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { CourseEnrollment, CourseEnrollmentCreate } from '@/types/enrollment'
import type { EnrollmentListParams } from '@/types/params'

export type { EnrollmentListParams } from '@/types/params'

/** GET /enroll/ — wajib login, filter `?course=`, `?user=`. */
export function listEnrollments(
  params?: EnrollmentListParams,
): Promise<Paginated<CourseEnrollment>> {
  return getJson<Paginated<CourseEnrollment>>('/enroll/', { params })
}

/** GET /enroll/{id}/ */
export function getEnrollment(id: number): Promise<CourseEnrollment> {
  return getJson<CourseEnrollment>(`/enroll/${id}/`)
}

/** POST /enroll/ — wajib isi `user` (backend tidak auto-inject). */
export function createEnrollment(
  payload: CourseEnrollmentCreate,
): Promise<CourseEnrollment> {
  return postJson<CourseEnrollment, CourseEnrollmentCreate>('/enroll/', payload)
}

/** PATCH /enroll/{id}/ */
export function updateEnrollment(
  id: number,
  payload: Partial<CourseEnrollmentCreate>,
): Promise<CourseEnrollment> {
  return patchJson<CourseEnrollment, Partial<CourseEnrollmentCreate>>(
    `/enroll/${id}/`,
    payload,
  )
}

/** DELETE /enroll/{id}/ */
export function deleteEnrollment(id: number): Promise<void> {
  return deleteJson(`/enroll/${id}/`)
}
