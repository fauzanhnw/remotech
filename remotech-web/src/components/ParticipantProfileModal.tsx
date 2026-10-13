import { useEffect, useState } from 'react'
import { Empty, Modal, Skeleton, Tag } from 'antd'

import { getUserEarnedBadges, notifyError } from '@/api'
import { badgeIconNode } from '@/components/badgeIcons'
import type { UserBadge } from '@/types/badge'
import type { Leaderboard } from '@/types/leaderboard'
import { levelColor, levelLabel } from '@/utils/level'

interface ParticipantProfileModalProps {
  open: boolean
  onClose: () => void
  /** Baris leaderboard peserta yang diklik (null = tertutup). */
  row: Leaderboard | null
}

/**
 * Modal profil peserta dari leaderboard: nama lengkap, level, dan badge
 * yang sudah diraih (GET /user-badge/earned/?user=). Nama/level/poin datang
 * dari baris leaderboard; badge di-fetch saat modal dibuka.
 */
export function ParticipantProfileModal({
  open,
  onClose,
  row,
}: ParticipantProfileModalProps) {
  const [badges, setBadges] = useState<UserBadge[]>([])
  const [loading, setLoading] = useState(false)

  const userId = row?.user ?? null

  // Reset + fetch saat modal dibuka untuk peserta berbeda.
  const [prevKey, setPrevKey] = useState<string | null>(null)
  const key = open && userId != null ? String(userId) : null
  if (prevKey !== key) {
    setPrevKey(key)
    if (key != null) {
      setBadges([])
      setLoading(true)
    }
  }

  useEffect(() => {
    if (userId == null || !open) return
    let cancelled = false

    getUserEarnedBadges(userId)
      .then((data) => {
        if (!cancelled) setBadges(data)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [userId, open])

  const name = row?.user_name ?? ''
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')

  return (
    <Modal
      open={open}
      title="Profil Peserta"
      footer={null}
      onCancel={onClose}
      destroyOnHidden
      width={520}
    >
      {row == null ? null : (
        <>
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-[#1677ff] text-xl font-semibold text-white">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold text-[#08060d]">
                {row.user_name}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <Tag color={levelColor(row.level)} className="mr-0">
                  {levelLabel(row.level, row.level_title)}
                </Tag>
                <span className="text-sm text-gray-500">
                  {row.total_points} poin
                </span>
              </div>
            </div>
          </div>

          <h3 className="mt-6 mb-3 text-base font-semibold text-[#08060d]">
            Badge
          </h3>
          {loading ? (
            <Skeleton active paragraph={{ rows: 2 }} />
          ) : badges.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Belum memiliki badge."
            />
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {badges.map((entry) => (
                <li
                  key={entry.id}
                  className="flex items-center gap-3 rounded-xl border border-gray-200 p-3"
                >
                  {entry.badge_detail.icon_image ? (
                    <img
                      src={entry.badge_detail.icon_image}
                      alt={entry.badge_detail.name}
                      className="h-10 w-10 shrink-0 rounded-full object-cover"
                    />
                  ) : (
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center text-2xl">
                      {badgeIconNode(entry.badge_detail.icon_name)}
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[#08060d]">
                      {entry.badge_detail.name}
                    </p>
                    <p className="truncate text-xs text-gray-500">
                      {entry.badge_detail.course_title}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Modal>
  )
}
