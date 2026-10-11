import { Modal, Typography } from 'antd'

import { badgeIconNode } from './badgeIcons'
import type { Badge } from '@/types/badge'

const { Paragraph, Text, Title } = Typography

interface BadgePreviewModalProps {
  badge: Badge
  onClose: () => void
}

/**
 * Preview ringkas badge pada halaman course publik: ikon, nama, deskripsi,
 * dan reward saja (tanpa tipe/status — data progres belum tersedia di sana).
 */
export function BadgePreviewModal({ badge, onClose }: BadgePreviewModalProps) {
  return (
    <Modal
      open
      title="Detail Badge"
      footer={null}
      centered
      onCancel={onClose}
      destroyOnHidden
      width={420}
    >
      <div className="flex flex-col items-center gap-1 text-center">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-100 text-3xl text-amber-500">
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
      </div>

      <div className="mt-4 space-y-3 text-sm">
        <div>
          <Text strong className="block text-[#08060d]">
            Deskripsi
          </Text>
          <Paragraph className="mb-0 mt-0.5 whitespace-pre-wrap text-gray-700">
            {badge.description}
          </Paragraph>
        </div>

        {badge.reward && (
          <div>
            <Text strong className="block text-[#08060d]">
              Hadiah
            </Text>
            <Paragraph className="mb-0 mt-0.5 whitespace-pre-wrap text-green-700">
              {badge.reward}
            </Paragraph>
          </div>
        )}
      </div>
    </Modal>
  )
}
