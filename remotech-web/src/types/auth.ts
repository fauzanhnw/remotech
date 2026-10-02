/** Payload & respons endpoint autentikasi. */

/** POST /register/ */
export interface RegisterPayload {
  email: string
  full_name: string
}

/** POST /token/ — `username` berisi alamat email (bukan username bebas). */
export interface LoginPayload {
  username: string
  password: string
}

/** POST /token/ */
export interface TokenPair {
  access: string
  refresh: string
}

/** POST /token/refresh/ — backend tidak merotasi refresh token. */
export interface RefreshPayload {
  refresh: string
}

export interface AccessTokenResponse {
  access: string
}

/** POST /set-password/ dan POST /forgot-password/reset/ */
export interface SetPasswordPayload {
  token: string
  password: string
  password_confirm: string
}

/** POST /forgot-password/ */
export interface ForgotPasswordPayload {
  email: string
}
