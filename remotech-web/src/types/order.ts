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
  user: number
  order_no: string
  transaction_status: OrderStatus
  gross_amount: string
  payment_type: string
  midtrans_transaction_id: string
  created_at: IsoDateTime
  paid_at: IsoDateTime | null
}

/** POST /order/ — semua field berikut wajib (backend tidak auto-inject user). */
export interface CourseOrderCreate {
  course: number
  user: number
  order_no: string
  gross_amount: string
  payment_type: string
  midtrans_transaction_id: string
  transaction_status?: OrderStatus
}
