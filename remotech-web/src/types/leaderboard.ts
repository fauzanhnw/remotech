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
  /** Urut poin tertinggi; course tanpa poin tetap ikut dengan `rank` null. */
  courses: MyLeaderboardCourse[]
}

/** GET /leaderboard/{id}/details/ — rincian poin satu peserta per module. */
export interface LeaderboardDetailEntry {
  id: number
  module: number | null
  /** Judul module (diisi saat sinkronisasi poin). */
  description: string
  point: number
}
