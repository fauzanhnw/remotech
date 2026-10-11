import { Tooltip, Typography } from 'antd'

import { badgeIconNode } from './badgeIcons'
import type { Badge, BadgeProgress } from '@/types/badge'

const { Text } = Typography

interface BadgeCardProps {
  badge: Badge
  /** True = badge sudah didapat (warna penuh); false = locked (grayscale). */
  earned: boolean
  /** Progres module course badge (untuk "x/y" pada badge locked). */
  progress?: BadgeProgress
  /** Tampilkan judul course di bawah nama (untuk tampilan lintas course). */
  showCourse?: boolean
  /** Klik kartu (mis. buka modal detail). */
  onClick?: () => void
}

/**
 * Kartu satu badge: earned = penuh warna; locked = grayscale + progres.
 * Render ikon: `icon_image` (upload) → `icon_name` (preset) → trophy.
 */
export function BadgeCard({
  badge,
  earned,
  progress,
  showCourse = false,
  onClick,
}: BadgeCardProps) {
  const clickable = onClick != null
  const lockedProgress =
    !earned && progress && progress.total > 0
      ? `${Math.min(progress.completed, progress.total)}/${progress.total}`
      : null
  const complete =
    lockedProgress != null && progress != null && progress.completed === progress.total

  return (
    <Tooltip title={badge.description}>
      <div
        role={clickable ? 'button' : undefined}
        tabIndex={clickable ? 0 : undefined}
        onClick={onClick}
        onKeyDown={
          clickable
            ? (event) => {
                if (event.key === 'Enter' || event.key === ' ') onClick()
              }
            : undefined
        }
        className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition ${
          earned
            ? 'border-amber-200 bg-amber-50/60'
            : 'border-gray-200 bg-white'
        } ${clickable ? 'cursor-pointer hover:shadow-md' : ''}`}
      >
        <span
          className={`flex h-14 w-14 items-center justify-center rounded-full text-2xl ${
            earned
              ? 'bg-amber-100 text-amber-500'
              : 'bg-gray-100 text-gray-400 grayscale'
          }`}
        >
          {badge.icon_image ? (
            <img
              src={badge.icon_image}
              alt={badge.name}
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            badgeIconNode(badge.icon_name)
          )}
        </span>
        <div>
          <Text
            strong
            className={`block ${earned ? 'text-[#08060d]' : 'text-gray-500'}`}
          >
            {badge.name}
          </Text>
          {showCourse && (
            <Text type="secondary" className="block text-xs">
              {badge.course_title}
            </Text>
          )}
          {!earned && lockedProgress && (
            <Text
              type={complete ? 'success' : 'secondary'}
              className="mt-1 block text-xs"
            >
              {complete ? 'Siap diklaim' : `${lockedProgress} module`}
            </Text>
          )}
          {earned && (
            <Text type="warning" className="mt-1 block text-xs">
              Didapat
            </Text>
          )}
        </div>
      </div>
    </Tooltip>
  )
}
