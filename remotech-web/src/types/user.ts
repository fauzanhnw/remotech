/** Profil user yang sedang login. */

/** GET /user/me/ — `full_name` fallback ke `username` (email) bila nama kosong. */
export interface CurrentUser {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  /** True bila user termasuk group `mentor`. */
  is_mentor: boolean
}

/**
 * PATCH /user/me/ — update nama & email (semua opsional).
 * `username` mengikuti `email` bila keduanya masih sama (identitas login).
 */
export interface ProfileUpdatePayload {
  first_name?: string
  last_name?: string
  email?: string
}

/** POST /user/change-password/ — wajib password lama, baru divalidasi backend. */
export interface ChangePasswordPayload {
  old_password: string
  new_password: string
  new_password_confirm: string
}
