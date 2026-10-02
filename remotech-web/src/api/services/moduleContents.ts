import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { ModuleContent, ModuleContentCreate } from '@/types/content'
import type { ModuleContentListParams } from '@/types/params'

export type { ModuleContentListParams } from '@/types/params'

/** GET /module-content/ — publik, filter `?module=`. */
export function listModuleContents(
  params?: ModuleContentListParams,
): Promise<Paginated<ModuleContent>> {
  return getJson<Paginated<ModuleContent>>('/module-content/', { params })
}

/** GET /module-content/{id}/ — publik. */
export function getModuleContent(id: number): Promise<ModuleContent> {
  return getJson<ModuleContent>(`/module-content/${id}/`)
}

/** POST /module-content/ — wajib pemilik course. */
export function createModuleContent(
  payload: ModuleContentCreate,
): Promise<ModuleContent> {
  return postJson<ModuleContent, ModuleContentCreate>('/module-content/', payload)
}

/** PATCH /module-content/{id}/ — wajib pemilik course. */
export function updateModuleContent(
  id: number,
  payload: Partial<ModuleContentCreate>,
): Promise<ModuleContent> {
  return patchJson<ModuleContent, Partial<ModuleContentCreate>>(
    `/module-content/${id}/`,
    payload,
  )
}

/** DELETE /module-content/{id}/ — wajib pemilik course (media orphan dibersihkan). */
export function deleteModuleContent(id: number): Promise<void> {
  return deleteJson(`/module-content/${id}/`)
}
