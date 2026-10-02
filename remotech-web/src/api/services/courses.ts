import { deleteJson, getJson, patchJson, postJson, toFormData } from './shared'
import type { Paginated } from '@/types/api'
import type { Course, CourseCreate } from '@/types/course'
import type { CourseListParams } from '@/types/params'

export type { CourseListParams } from '@/types/params'

/** GET /course/ — publik, terpaginasi (10/halaman). */
export function listCourses(params?: CourseListParams): Promise<Paginated<Course>> {
  return getJson<Paginated<Course>>('/course/', { params })
}

/** GET /course/{id}/ — publik. */
export function getCourse(id: number): Promise<Course> {
  return getJson<Course>(`/course/${id}/`)
}

/** POST /course/ — otomatis mengisi `user` dari token. Multipart bila ada thumbnail. */
export function createCourse(payload: CourseCreate): Promise<Course> {
  const body = payload.thumbnail
    ? toFormData(payload as unknown as Record<string, unknown>)
    : payload
  return postJson<Course, FormData | CourseCreate>('/course/', body)
}

/** PATCH /course/{id}/ — sebagian. Multipart bila ada thumbnail. */
export function updateCourse(id: number, payload: Partial<CourseCreate>): Promise<Course> {
  const body = payload.thumbnail
    ? toFormData(payload as unknown as Record<string, unknown>)
    : payload
  return patchJson<Course, FormData | Partial<CourseCreate>>(`/course/${id}/`, body)
}

/** DELETE /course/{id}/ */
export function deleteCourse(id: number): Promise<void> {
  return deleteJson(`/course/${id}/`)
}
