/** Badge per course: definisi, kepemilikan user, dan progres earned/locked. */

/** Aturan pemberian badge: otomatis (course lengkap) atau manual oleh mentor. */
export type BadgeRuleType = 'course_complete' | 'manual'

/**
 * GET /badge/{id}/ — `icon_image` URL absolut media (null bila kosong),
 * `icon_name` ikon preset frontend (kosong = fallback trophy),
 * `reward` teks hadiah informatif (kosong = tanpa reward).
 */
export interface Badge {
  id: number
  course: number
  course_title: string
  name: string
  description: string
  /** Teks hadiah saat badge didapat; "" bila tidak ada. */
  reward: string
  icon_image: string | null
  icon_name: string
  rule_type: BadgeRuleType
}

/** POST /badge/ — tulis hanya pemilik course (multipart bila unggah ikon). */
export interface BadgeCreate {
  course: number
  name: string
  description: string
  /** Teks hadiah informatif (opsional). */
  reward?: string
  icon_image?: File | null
  icon_name?: string
  rule_type?: BadgeRuleType
}

/** GET /user-badge/{id}/ — baris kepemilikan + turunan tampilan. */
export interface UserBadge {
  id: number
  user: number
  /** Nama lengkap pemilik; fallback username. */
  user_name: string
  badge: number
  badge_detail: Badge
  course: number
  course_title: string
  earned_at: string
  /** "system" untuk otomatis; username mentor untuk manual. */
  awarded_by: string
}

/** POST /user-badge/ — mentor memberi badge manual ke student enrolled. */
export interface UserBadgeAwardPayload {
  badge: number
  user: number
}

/** Progres module pada course badge (untuk menampilkan "x/y" di locked). */
export interface BadgeProgress {
  completed: number
  total: number
}

/** GET /user-badge/me/ — definisi badge course yang di-enroll + status. */
export interface MyBadgeEntry {
  badge: Badge
  earned: boolean
  course: number
  progress: BadgeProgress
  /** ISO datetime saat badge didapat; null bila masih locked. */
  earned_at: string | null
  /**
   * "system" untuk otomatis; "Nama Lengkap - email" mentor (fallback
   * email/username) untuk manual; "" bila locked.
   */
  awarded_by: string
}
