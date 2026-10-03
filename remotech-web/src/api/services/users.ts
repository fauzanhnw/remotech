import { getJson } from './shared'
import type { CurrentUser } from '@/types/user'

/** GET /user/me/ — profil user yang sedang login (wajib token). */
export function getMe(): Promise<CurrentUser> {
  return getJson<CurrentUser>('/user/me/')
}
