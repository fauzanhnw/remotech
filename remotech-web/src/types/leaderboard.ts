/** Papan skor per course. */

/** GET /leaderboard/{id}/ — `course_title` diturunkan dari relasi course. */
export interface Leaderboard {
  id: number
  course: number
  course_title: string
  user: number
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
