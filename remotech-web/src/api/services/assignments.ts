import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { Assignment, AssignmentCreate } from '@/types/content'
import type { AssignmentListParams } from '@/types/params'

export type { AssignmentListParams } from '@/types/params'

/** GET /assignment/ — wajib login, filter `?course_module=`. */
export function listAssignments(
  params?: AssignmentListParams,
): Promise<Paginated<Assignment>> {
  return getJson<Paginated<Assignment>>('/assignment/', { params })
}

/** GET /assignment/{id}/ */
export function getAssignment(id: number): Promise<Assignment> {
  return getJson<Assignment>(`/assignment/${id}/`)
}

/** POST /assignment/ */
export function createAssignment(payload: AssignmentCreate): Promise<Assignment> {
  return postJson<Assignment, AssignmentCreate>('/assignment/', payload)
}

/** PATCH /assignment/{id}/ */
export function updateAssignment(
  id: number,
  payload: Partial<AssignmentCreate>,
): Promise<Assignment> {
  return patchJson<Assignment, Partial<AssignmentCreate>>(`/assignment/${id}/`, payload)
}

/** DELETE /assignment/{id}/ */
export function deleteAssignment(id: number): Promise<void> {
  return deleteJson(`/assignment/${id}/`)
}
