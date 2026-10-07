import type { AxiosRequestConfig } from 'axios'

import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { CourseModule, CourseModuleCreate } from '@/types/course'
import type { ModuleListParams } from '@/types/params'

export type { ModuleListParams } from '@/types/params'

/** GET /module/ — publik, filter `?course=`. */
export function listModules(params?: ModuleListParams): Promise<Paginated<CourseModule>> {
  return getJson<Paginated<CourseModule>>('/module/', { params })
}

/** GET /module/{id}/ — publik. */
export function getModule(id: number): Promise<CourseModule> {
  return getJson<CourseModule>(`/module/${id}/`)
}

/** POST /module/ — hanya pemilik course (403 bila bukan owner). */
export function createModule(
  payload: CourseModuleCreate,
  config?: AxiosRequestConfig,
): Promise<CourseModule> {
  return postJson<CourseModule, CourseModuleCreate>('/module/', payload, config)
}

/** PATCH /module/{id}/ — hanya pemilik course. */
export function updateModule(
  id: number,
  payload: Partial<CourseModuleCreate>,
  config?: AxiosRequestConfig,
): Promise<CourseModule> {
  return patchJson<CourseModule, Partial<CourseModuleCreate>>(
    `/module/${id}/`,
    payload,
    config,
  )
}

/** DELETE /module/{id}/ — hanya pemilik course. */
export function deleteModule(id: number): Promise<void> {
  return deleteJson(`/module/${id}/`)
}
