import { deleteJson, getJson, patchJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { Leaderboard, LeaderboardCreate } from '@/types/leaderboard'
import type { LeaderboardListParams } from '@/types/params'

export type { LeaderboardListParams } from '@/types/params'

/** GET /leaderboard/ — wajib login, filter `?course=`, `?user=`. */
export function listLeaderboards(
  params?: LeaderboardListParams,
): Promise<Paginated<Leaderboard>> {
  return getJson<Paginated<Leaderboard>>('/leaderboard/', { params })
}

/** GET /leaderboard/{id}/ */
export function getLeaderboard(id: number): Promise<Leaderboard> {
  return getJson<Leaderboard>(`/leaderboard/${id}/`)
}

/** POST /leaderboard/ — wajib isi `user` (backend tidak auto-inject). */
export function createLeaderboard(payload: LeaderboardCreate): Promise<Leaderboard> {
  return postJson<Leaderboard, LeaderboardCreate>('/leaderboard/', payload)
}

/** PATCH /leaderboard/{id}/ */
export function updateLeaderboard(
  id: number,
  payload: Partial<LeaderboardCreate>,
): Promise<Leaderboard> {
  return patchJson<Leaderboard, Partial<LeaderboardCreate>>(
    `/leaderboard/${id}/`,
    payload,
  )
}

/** DELETE /leaderboard/{id}/ */
export function deleteLeaderboard(id: number): Promise<void> {
  return deleteJson(`/leaderboard/${id}/`)
}
