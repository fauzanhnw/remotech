/** Bonus poin manual mentor ke student enrolled (endpoint /point-bonus/). */

/** GET/POST /point-bonus/ — baris LeaderboardDetail `is_manual` (module null). */
export interface PointBonus {
  id: number
  user: number
  user_name: string
  course: number
  course_title: string
  point: number
  description: string
  /** Username mentor pemberi. */
  awarded_by: string
}

/** POST /point-bonus/ — mentor pemilik course memberi bonus ke student enrolled. */
export interface PointBonusCreate {
  course: number
  user: number
  /** Minimal 1 (divalidasi backend). */
  point: number
  description: string
}
