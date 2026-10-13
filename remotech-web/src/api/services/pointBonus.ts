import { deleteJson, getJson, postJson } from './shared'
import type { Paginated } from '@/types/api'
import type { PointBonus, PointBonusCreate } from '@/types/pointBonus'
import type { PointBonusListParams } from '@/types/params'

export type { PointBonusListParams } from '@/types/params'

/**
 * GET /point-bonus/ — riwayat bonus poin manual per course.
 * Hanya mengembalikan bonus milik course yang dimiliki (superuser: semua).
 */
export function listPointBonuses(
  params?: PointBonusListParams,
): Promise<Paginated<PointBonus>> {
  return getJson<Paginated<PointBonus>>('/point-bonus/', { params })
}

/** POST /point-bonus/ — mentor pemilik course memberi bonus ke student enrolled. */
export function createPointBonus(payload: PointBonusCreate): Promise<PointBonus> {
  return postJson<PointBonus, PointBonusCreate>('/point-bonus/', payload)
}

/** DELETE /point-bonus/{id}/ — cabut bonus + sinkron ulang poin peserta. */
export function deletePointBonus(id: number): Promise<void> {
  return deleteJson(`/point-bonus/${id}/`)
}
