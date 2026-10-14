import { Modal, Tag, Typography } from 'antd'

import { badgeIconNode } from './badgeIcons'
import type { MyBadgeEntry } from '@/types/badge'

const { Paragraph, Text, Title } = Typography

interface BadgeDetailModalProps {
  entry: MyBadgeEntry
  onClose: () => void
}

/** Label pemberi badge (sama makna dengan tooltip daftar mentor). */
function awardedByLabel(awardedBy: string): string {
  if (awardedBy === 'system') return 'Awarded by system (automatic)'
  return `Awarded by mentor: ${awardedBy}`
}

/**
 * Detail satu badge saat kartu diklik (read-only). Menampilkan deskripsi,
 * reward, tipe, dan status (progres locked / "Didapat" + tanggal + pemberi).
 */
export function BadgeDetailModal({ entry, onClose }: BadgeDetailModalProps) {
  const { badge, earned, progress, earned_at: earnedAt, awarded_by: awardedBy } = entry
  const lockedProgress =
    !earned && progress.total > 0
      ? `${Math.min(progress.completed, progress.total)}/${progress.total}`
      : null
  const complete =
    lockedProgress != null && progress.completed === progress.total

  return (
    <Modal
      open
      title="Detail Badge"
      footer={null}
      centered
      onCancel={onClose}
      destroyOnHidden
      width={480}
    >
      <div className="flex flex-col items-center gap-1 text-center">
        <span
          className={`flex h-16 w-16 items-center justify-center rounded-full text-3xl ${
            earned ? 'bg-amber-100 text-amber-500' : 'bg-gray-100 text-gray-400 grayscale'
          }`}
        >
          {badge.icon_image ? (
            <img
              src={badge.icon_image}
              alt={badge.name}
              className="h-12 w-12 rounded-full object-cover"
            />
          ) : (
            badgeIconNode(badge.icon_name)
          )}
        </span>
        <Title level={4} className="mb-0 mt-2 text-[#08060d]">
          {badge.name}
        </Title>
        <Text type="secondary" className="text-xs">
          {badge.course_title}
        </Text>
      </div>

      <div className="mt-4 space-y-3 text-sm">
        <div>
          <Text strong className="block text-[#08060d]">
            Description
          </Text>
          <Paragraph className="mb-0 mt-0.5 whitespace-pre-wrap text-gray-700">
            {badge.description}
          </Paragraph>
        </div>

        {badge.reward && (
          <div>
            <Text strong className="block text-[#08060d]">
              Reward
            </Text>
            <Paragraph className="mb-0 mt-0.5 whitespace-pre-wrap text-green-700">
              {badge.reward}
            </Paragraph>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Text strong className="text-[#08060d]">
            Type
          </Text>
          <Tag color={badge.rule_type === 'course_complete' ? 'blue' : 'default'}>
            {badge.rule_type === 'course_complete' ? 'Automatic' : 'Manual'}
          </Tag>
        </div>

        <div>
          <Text strong className="block text-[#08060d]">
            Status
          </Text>
          {earned ? (
            <div className="mt-0.5 space-y-0.5">
              <Text type="success">Earned</Text>
              {earnedAt && (
                <Text type="secondary" className="block">
                  {new Date(earnedAt).toLocaleDateString('en-US', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                  })}
                </Text>
              )}
              <Text type="secondary" className="block">
                {awardedByLabel(awardedBy)}
              </Text>
            </div>
          ) : (
            <Text type="secondary" className="mt-0.5 block">
              {lockedProgress != null
                ? complete
                  ? 'Ready to claim'
                  : `${lockedProgress} modules completed`
                : 'Not earned yet'}
            </Text>
          )}
        </div>
      </div>
    </Modal>
  )
}
