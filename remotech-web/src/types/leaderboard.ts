/** Papan skor per course. */

/** GET /leaderboard/{id}/ */
export interface Leaderboard {
  id: number
  course: number
  user: number
  total_points: number
}

/** POST /leaderboard/ — backend tidak auto-inject user. */
export interface LeaderboardCreate {
  course: number
  user: number
  total_points?: number
}
