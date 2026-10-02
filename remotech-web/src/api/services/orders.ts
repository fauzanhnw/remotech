import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { CourseOrder, CourseOrderCreate } from '@/types/order'
import type { OrderListParams } from '@/types/params'

export type { OrderListParams } from '@/types/params'

/** GET /order/ — wajib login, filter `?course=`, `?user=`, `?transaction_status=`. */
export function listOrders(params?: OrderListParams): Promise<Paginated<CourseOrder>> {
  return getJson<Paginated<CourseOrder>>('/order/', { params })
}

/** GET /order/{id}/ */
export function getOrder(id: number): Promise<CourseOrder> {
  return getJson<CourseOrder>(`/order/${id}/`)
}

/** POST /order/ — wajib isi `user` (backend tidak auto-inject). */
export function createOrder(payload: CourseOrderCreate): Promise<CourseOrder> {
  return postJson<CourseOrder, CourseOrderCreate>('/order/', payload)
}

/** PATCH /order/{id}/ */
export function updateOrder(
  id: number,
  payload: Partial<CourseOrderCreate>,
): Promise<CourseOrder> {
  return patchJson<CourseOrder, Partial<CourseOrderCreate>>(`/order/${id}/`, payload)
}

/** DELETE /order/{id}/ */
export function deleteOrder(id: number): Promise<void> {
  return deleteJson(`/order/${id}/`)
}
