import { getJson, patchJson, postJson } from './shared'
import type { MessageResponse } from '@/types/api'
import type {
  ChangePasswordPayload,
  CurrentUser,
  ProfileUpdatePayload,
} from '@/types/user'

/** GET /user/me/ — profil user yang sedang login (wajib token). */
export function getMe(): Promise<CurrentUser> {
  return getJson<CurrentUser>('/user/me/')
}

/** PATCH /user/me/ — update nama & email; membalas profil terbaru. */
export function updateProfile(payload: ProfileUpdatePayload): Promise<CurrentUser> {
  return patchJson<CurrentUser, ProfileUpdatePayload>('/user/me/', payload, {
    meta: { suppressErrorToast: true },
  })
}

/** POST /user/change-password/ — ganti password (verifikasi password lama). */
export function changePassword(payload: ChangePasswordPayload): Promise<MessageResponse> {
  return postJson<MessageResponse, ChangePasswordPayload>(
    '/user/change-password/',
    payload,
    { meta: { suppressErrorToast: true } },
  )
}
