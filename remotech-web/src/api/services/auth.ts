import { tokenStorage } from '../tokenStorage'
import { postJson } from './shared'
import type {
  ForgotPasswordPayload,
  LoginPayload,
  RegisterPayload,
  SetPasswordPayload,
  TokenPair,
} from '@/types/auth'
import type { MessageResponse } from '@/types/api'

/**
 * Login — backend memakai field `username` berisi alamat email.
 * Token langsung disimpan di localStorage.
 */
export async function login(payload: LoginPayload): Promise<TokenPair> {
  const tokens = await postJson<TokenPair, LoginPayload>('/token/', payload, {
    meta: { suppressErrorToast: true },
  })
  tokenStorage.setPair(tokens)
  return tokens
}

/**
 * Logout — backend tidak punya endpoint logout/blacklist,
 * jadi token dibuang di sisi client saja.
 */
export function logout(): void {
  tokenStorage.clear()
}

/** POST /register/ — backend mengirim email set-password ke user. */
export function register(payload: RegisterPayload): Promise<MessageResponse> {
  return postJson<MessageResponse, RegisterPayload>('/register/', payload, {
    meta: { suppressErrorToast: true },
  })
}

/** POST /set-password/ — set password dari token di email. */
export function setPassword(payload: SetPasswordPayload): Promise<MessageResponse> {
  return postJson<MessageResponse, SetPasswordPayload>('/set-password/', payload, {
    meta: { suppressErrorToast: true },
  })
}

/** POST /forgot-password/ — selalu 200 meski email tidak terdaftar. */
export function forgotPassword(payload: ForgotPasswordPayload): Promise<MessageResponse> {
  return postJson<MessageResponse, ForgotPasswordPayload>('/forgot-password/', payload, {
    meta: { suppressErrorToast: true },
  })
}

/** POST /forgot-password/reset/ — reset password dari token di email. */
export function resetPassword(payload: SetPasswordPayload): Promise<MessageResponse> {
  return postJson<MessageResponse, SetPasswordPayload>('/forgot-password/reset/', payload, {
    meta: { suppressErrorToast: true },
  })
}
