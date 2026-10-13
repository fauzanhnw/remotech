/** Papan skor per course. */

/** GET /leaderboard/{id}/ — `course_title`/`user_name` diturunkan dari relasi. */
export interface Leaderboard {
  id: number
  course: number
  course_title: string
  user: number
  /** Nama lengkap peserta; fallback ke username/email. */
  user_name: string
  total_points: number
  /** Level on-the-fly dari total poin lintas course (1-based). */
  level: number
  /** Nama level: Pemula · Pelajar · Praktisi · Profesional · Ahli · Master. */
  level_title: string
}

/** POST /leaderboard/ — backend tidak auto-inject user. */
export interface LeaderboardCreate {
  course: number
  user: number
  total_points?: number
}

/** GET /leaderboard/me/ — satu course pada ringkasan poin milik sendiri. */
export interface MyLeaderboardCourse {
  course: number
  course_title: string
  total_points: number
  /** Null bila belum pernah menyelesaikan module pada course ini. */
  rank: number | null
  /** Jumlah peserta yang punya baris leaderboard di course ini. */
  participants: number
}

/** GET /leaderboard/me/ — total poin lintas course (hanya course yang di-enroll). */
export interface MyLeaderboard {
  total_points: number
  /** Level on-the-fly dari total_points (1-based). */
  level: number
  /** Nama level: Pemula · Pelajar · Praktisi · Profesional · Ahli · Master. */
  level_title: string
  /** Nama level berikutnya; null bila sudah level maksimal (Master). */
  next_level_title: string | null
  /** Poin yang kurang ke level berikutnya; null bila sudah level maksimal. */
  points_to_next_level: number | null
  /** Persen progres menuju level berikutnya (0–100; 100 di level maksimal). */
  level_progress: number
  /** Urut poin tertinggi; course tanpa poin tetap ikut dengan `rank` null. */
  courses: MyLeaderboardCourse[]
}

/** GET /leaderboard/{id}/details/ — rincian poin satu peserta per module. */
export interface LeaderboardDetailEntry {
  id: number
  module: number | null
  /** Judul module (diisi saat sinkronisasi poin) atau alasan bonus manual. */
  description: string
  point: number
  /** True untuk baris bonus manual mentor (module null — bukan hasil sync). */
  is_manual: boolean
  /** Username mentor pemberi bonus (kosong untuk baris hasil sync module). */
  awarded_by: string
}
