import { getJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { CourseOrder, EnrollCoursePayload, EnrollCourseResponse } from '@/types/order'
import type { OrderListParams } from '@/types/params'

export type { OrderListParams } from '@/types/params'

/** GET /order/ — wajib login, hanya order milik sendiri. Filter `?course=`, `?user=`, `?transaction_status=`. */
export function listOrders(params?: OrderListParams): Promise<Paginated<CourseOrder>> {
  return getJson<Paginated<CourseOrder>>('/order/', { params })
}

/** GET /order/{id}/ — hanya order milik sendiri (404 bila milik user lain). */
export function getOrder(id: number): Promise<CourseOrder> {
  return getJson<CourseOrder>(`/order/${id}/`)
}

/**
 * POST /order/enroll/ — enroll/beli course.
 *
 * - Course gratis: `enrolled: true` + order langsung `settlement`, tanpa Snap.
 * - Course berbayar: `enrolled: false` + order `pending` + `snap_token` —
 *   buka popup Snap (`payWithSnap`), lalu konfirmasi dengan `checkPayment`.
 * - Course hanya bisa dibeli sekali; order `pending` lama dipakai ulang,
 *   order gagal (deny/cancel/expire/failure) menghasilkan order baru.
 * - Error umum: 400 (sudah dibeli / belum publish), 502 (gateway bermasalah).
 */
export function enrollCourse(course: number): Promise<EnrollCourseResponse> {
  return postJson<EnrollCourseResponse, EnrollCoursePayload>('/order/enroll/', {
    course,
  })
}

/**
 * POST /order/{id}/check-payment/ — tanya status terbaru ke Midtrans dan
 * sinkronkan order (otomatis membuat enrollment bila sudah sukses).
 * Pelengkap webhook; dipanggil setelah popup Snap ditutup / tombol "cek ulang".
 */
export function checkPayment(id: number): Promise<CourseOrder> {
  return postJson<CourseOrder>(`/order/${id}/check-payment/`)
}
