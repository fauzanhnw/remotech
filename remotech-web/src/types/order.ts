/** Order pembelian course (terkait Midtrans). */

import type { IsoDateTime } from './common'

export type OrderStatus =
  | 'settlement'
  | 'pending'
  | 'deny'
  | 'cancel'
  | 'expire'
  | 'failure'

/** GET /order/{id}/ — `gross_amount` ter-serial sebagai string decimal. */
export interface CourseOrder {
  id: number
  course: number
  /** Judul course (diturunkan dari relasi, bukan kolom order). */
  course_title: string
  user: number
  order_no: string
  transaction_status: OrderStatus
  gross_amount: string
  payment_type: string
  midtrans_transaction_id: string
  /** Token Snap; kosong untuk course gratis atau sebelum Snap dibuat. */
  snap_token: string
  created_at: IsoDateTime
  paid_at: IsoDateTime | null
}

/** POST /order/enroll/ — body minimal untuk enroll/beli course. */
export interface EnrollCoursePayload {
  course: number
}

/**
 * POST /order/enroll/
 *
 * - Course gratis: `enrolled: true`, order langsung `settlement`.
 * - Course berbayar: `enrolled: false`, order `pending` — buka Snap dengan
 *   `snap_token`, lalu konfirmasi via `checkPayment(order.id)`.
 * - Satu course hanya bisa dibeli sekali (backend membalas 400 bila sudah).
 */
export interface EnrollCourseResponse {
  order: CourseOrder
  enrolled: boolean
  snap_token: string
}
