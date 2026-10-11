/** Progres belajar per module (ditandai selesai lewat halaman detail). */

import type { IsoDateTime } from './common'
import type { Badge } from './badge'

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

/** POST /progress/ — baris progres + badge baru yang didapat (jika ada). */
export interface UserProgressCreateResult extends UserProgress {
  earned_badges: Badge[]
}

/** GET /progress/summary/ — ringkasan progres semua course yang di-enroll. */
export interface CourseProgressSummary {
  course: number
  /** Jumlah module pada course. */
  total: number
  /** Jumlah module yang ditandai selesai user. */
  completed: number
  /** Persen pembulatan (bila `total` 0). */
  percent: number
}

/** GET /progress/activity/ — satu hari pada grafik streak (zona WIB). */
export interface DayActivity {
  /** Tanggal ISO `YYYY-MM-DD` dalam zona WIB. */
  date: string
  /** Hari dalam minggu: Senin = 0 … Minggu = 6. */
  weekday: number
  /** True bila ada aktivitas (buka konten / selesai module / submit) hari itu. */
  active: boolean
  /** Jumlah kejadian aktivitas hari itu. */
  count: number
}

/**
 * GET /progress/activity/ — grafik 7 hari terakhir (terakhir = hari ini)
 * plus streak belajar; hari dihitung dalam zona WIB.
 */
export interface WeeklyActivity {
  days: DayActivity[]
  /** Hari beruntun sampai hari ini; bila hari ini belum aktif, berawal dari kemarin. */
  current_streak: number
  /** Hari beruntun terpanjang dalam 365 hari terakhir. */
  best_streak: number
  /** Jumlah hari aktif di antara 7 hari `days`. */
  week_active_count: number
}
