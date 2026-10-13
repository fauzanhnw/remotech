import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { Badge, BadgeCreate, MyBadgeEntry, UserBadge, UserBadgeAwardPayload } from '@/types/badge'
import type { BadgeListParams, UserBadgeListParams } from '@/types/params'

export type { BadgeListParams, UserBadgeListParams } from '@/types/params'

/** GET /badge/ — public, filter `?course=`, `?rule_type=`. */
export function listBadges(params?: BadgeListParams): Promise<Paginated<Badge>> {
  return getJson<Paginated<Badge>>('/badge/', { params })
}

/** GET /badge/{id}/ */
export function getBadge(id: number): Promise<Badge> {
  return getJson<Badge>(`/badge/${id}/`)
}

/**
 * POST /badge/ — hanya pemilik course. `icon_image` opsional (File, multipart).
 * Kirim sebagai FormData bila ada unggahan ikon.
 */
export function createBadge(
  payload: BadgeCreate | FormData,
): Promise<Badge> {
  return postJson<Badge, BadgeCreate | FormData>('/badge/', payload)
}

/** PATCH /badge/{id}/ — hanya pemilik course. */
export function updateBadge(
  id: number,
  payload: Partial<BadgeCreate> | FormData,
): Promise<Badge> {
  return patchJson<Badge, Partial<BadgeCreate> | FormData>(
    `/badge/${id}/`,
    payload,
  )
}

/** DELETE /badge/{id}/ — hanya pemilik course (204 tanpa body). */
export function deleteBadge(id: number): Promise<void> {
  return deleteJson(`/badge/${id}/`)
}

/**
 * GET /user-badge/ — baris milik sendiri (superuser: semua).
 * Filter `?badge=`, `?user=`, `?badge__course=`.
 */
export function listUserBadges(
  params?: UserBadgeListParams,
): Promise<Paginated<UserBadge>> {
  return getJson<Paginated<UserBadge>>('/user-badge/', { params })
}

/**
 * GET /user-badge/me/ — badge course yang di-enroll: earned + locked
 * dengan progres module (x/y). Filter `?course=`.
 */
export function getMyBadges(course?: number): Promise<MyBadgeEntry[]> {
  return getJson<MyBadgeEntry[]>('/user-badge/me/', {
    params: course != null ? { course } : undefined,
  })
}

/** POST /user-badge/ — mentor award badge manual ke student enrolled. */
export function awardBadge(payload: UserBadgeAwardPayload): Promise<UserBadge> {
  return postJson<UserBadge, UserBadgeAwardPayload>('/user-badge/', payload)
}

/**
 * GET /user-badge/earned/?user= — badge yang sudah didapat user tertentu
 * (modal profil peserta dari leaderboard). Read-only untuk semua user login.
 */
export function getUserEarnedBadges(userId: number): Promise<UserBadge[]> {
  return getJson<UserBadge[]>('/user-badge/earned/', { params: { user: userId } })
}

/** DELETE /user-badge/{id}/ — cabut badge (pemilik course / superuser). */
export function revokeBadge(id: number): Promise<void> {
  return deleteJson(`/user-badge/${id}/`)
}
