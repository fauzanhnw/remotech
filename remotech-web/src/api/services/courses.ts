import type { AxiosRequestConfig } from 'axios'

import { deleteJson, getJson, patchJson, postJson, toFormData } from './shared'
import type { Paginated } from '@/types/api'
import type { Course, CourseCreate, CourseUpdate } from '@/types/course'
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

/** GET /course/my/ — course milik user login (termasuk draft), terpaginasi. */
export function listMyCourses(params?: CourseListParams): Promise<Paginated<Course>> {
  return getJson<Paginated<Course>>('/course/my/', { params })
}

/** POST /course/ — otomatis mengisi `user` dari token. Multipart bila ada thumbnail. */
export function createCourse(payload: CourseCreate): Promise<Course> {
  const body = payload.thumbnail
    ? toFormData(payload as unknown as Record<string, unknown>)
    : payload
  return postJson<Course, FormData | CourseCreate>('/course/', body, {
    meta: { suppressErrorToast: true },
  })
}

/** PATCH /course/{id}/ — sebagian. Multipart bila thumbnail diganti/dihapus (`''`). */
export function updateCourse(
  id: number,
  payload: CourseUpdate,
  config?: AxiosRequestConfig,
): Promise<Course> {
  const useFormData =
    payload.thumbnail instanceof File || payload.thumbnail === ''
  const body = useFormData
    ? toFormData(payload as unknown as Record<string, unknown>)
    : payload
  return patchJson<Course, FormData | CourseUpdate>(`/course/${id}/`, body, config)
}

/** DELETE /course/{id}/ */
export function deleteCourse(id: number): Promise<void> {
  return deleteJson(`/course/${id}/`)
}
