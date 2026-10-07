/** Progres belajar per module (ditandai selesai lewat halaman detail). */

import type { IsoDateTime } from './common'

/** GET /progress/ — hanya baris milik sendiri. */
export interface UserProgress {
  id: number
  module: number
  status: 'unfinish' | 'finish'
  complete_at: IsoDateTime | null
}

/** POST /progress/ — body hanya `{ module }`, status diisi backend (`finish`). */
export interface UserProgressCreate {
  module: number
}

/** GET /progress/summary/ — ringkasan progres semua course yang di-enroll. */
export interface CourseProgressSummary {
  course: number
  /** Jumlah module pada course. */
  total: number
  /** Jumlah module yang ditandai selesai user. */
  completed: number
  /** Persen pembulatan (0 bila `total` 0). */
  percent: number
}
