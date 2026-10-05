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
