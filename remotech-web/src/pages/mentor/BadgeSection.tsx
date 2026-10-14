import { EditOutlined, PlusOutlined, GiftOutlined, DeleteOutlined } from '@ant-design/icons'
import { Button, Empty, Popconfirm, Skeleton, Tag, Tooltip } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import {
  deleteBadge,
  listBadges,
  listUserBadges,
  notifyError,
  notifySuccess,
  revokeBadge,
} from '@/api'
import { badgeIconNode } from '@/components/badgeIcons'
import { fetchAllPages } from '@/utils/paginate'
import type { Badge } from '@/types/badge'
import type { UserBadge } from '@/types/badge'
import { AwardBadgeModal } from './AwardBadgeModal'
import { BadgeFormModal } from './BadgeFormModal'

interface BadgeSectionProps {
  courseId: number
  /** false = tampilan baca-saja (bukan pemilik course). */
  canManage: boolean
}

/**
 * Kelola badge course (mentor): CRUD definisi + pemberian/cabutan badge
 * manual ke student enrolled.
 */
export function BadgeSection({ courseId, canManage }: BadgeSectionProps) {
  // Null = belum termuat (skeleton); reload mengganti isi langsung.
  const [badges, setBadges] = useState<Badge[] | null>(null)
  const [holders, setHolders] = useState<Record<number, UserBadge[]>>({})
  const [reloadKey, setReloadKey] = useState(0)

  const [formModal, setFormModal] = useState<{
    open: boolean
    badge: Badge | null
  }>({ open: false, badge: null })
  const [awardModal, setAwardModal] = useState<{
    open: boolean
    badge: Badge | null
  }>({ open: false, badge: null })

  const reload = useCallback(() => setReloadKey((value) => value + 1), [])

  useEffect(() => {
    let cancelled = false

    fetchAllPages((params) => listBadges({ ...params, course: courseId }))
      .then(async (items) => {
        if (cancelled) return
        setBadges(items)
        // Pemegang badge per definisi (baris user-badge course ini).
        const rows = await fetchAllPages((params) =>
          listUserBadges({ ...params, badge__course: courseId }),
        )
        if (cancelled) return
        const grouped: Record<number, UserBadge[]> = {}
        for (const row of rows) {
          ;(grouped[row.badge] ??= []).push(row)
        }
        setHolders(grouped)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, reloadKey])

  const handleDelete = async (badge: Badge) => {
    try {
      await deleteBadge(badge.id)
      notifySuccess('Badge deleted.')
      reload()
    } catch (error) {
      notifyError(error)
    }
  }

  const handleRevoke = async (row: UserBadge) => {
    try {
      await revokeBadge(row.id)
      notifySuccess('Badge revoked.')
      reload()
    } catch (error) {
      notifyError(error)
    }
  }

  const ruleLabel: Record<string, string> = {
    course_complete: 'Automatic',
    manual: 'Manual',
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-10 md:mx-8 xl:px-16">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#08060d]">Badge</h2>
          <p className="mt-1 text-sm text-gray-600">
            Automatic badges are awarded by the system when all modules are
            complete; manual badges are awarded to enrolled students.
          </p>
        </div>
        {canManage && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setFormModal({ open: true, badge: null })}
          >
            Create Badge
          </Button>
        )}
      </div>

      {badges === null ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : badges.length === 0 ? (
        <Empty description="No badges for this course yet." className="py-10">
          {canManage && (
            <Button type="primary" onClick={() => setFormModal({ open: true, badge: null })}>
              Create First Badge
            </Button>
          )}
        </Empty>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {badges.map((badge) => (
            <div
              key={badge.id}
              className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-50 text-xl text-amber-500">
                  {badge.icon_image ? (
                    <img
                      src={badge.icon_image}
                      alt={badge.name}
                      className="h-9 w-9 rounded-full object-cover"
                    />
                  ) : (
                    badgeIconNode(badge.icon_name)
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-[#08060d]">{badge.name}</p>
                  <p className="mt-0.5 line-clamp-2 text-sm text-gray-500">
                    {badge.description}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Tag
                      color={badge.rule_type === 'course_complete' ? 'blue' : 'default'}
                      className="mr-0"
                    >
                      {ruleLabel[badge.rule_type] ?? badge.rule_type}
                    </Tag>
                    {badge.reward && (
                      <Tooltip title={badge.reward}>
                        <Tag color="gold" className="mr-0 line-clamp-1 max-w-full">
                          {badge.reward}
                        </Tag>
                      </Tooltip>
                    )}
                  </div>
                </div>
              </div>

              {(holders[badge.id]?.length ?? 0) > 0 && (
                <div className="border-t border-gray-100 pt-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Recipients ({holders[badge.id].length})
                  </p>
                  <ul className="mt-1 space-y-1">
                    {holders[badge.id].map((row) => (
                      <li
                        key={row.id}
                        className="flex items-center justify-between gap-2 text-sm text-gray-600"
                      >
                        <span className="truncate">{row.user_name}</span>
                        <span className="flex items-center gap-1">
                          <Tooltip
                            title={
                              row.awarded_by === 'system'
                                ? 'Automatic (system)'
                                : `Awarded by mentor: ${row.awarded_by}`
                            }
                          >
                            <Tag
                              color={row.awarded_by === 'system' ? 'green' : 'purple'}
                              className="mr-0"
                            >
                              {row.awarded_by === 'system' ? 'System' : 'Mentor'}
                            </Tag>
                          </Tooltip>
                          {canManage && row.awarded_by !== 'system' && (
                            <Popconfirm
                              title="Revoke this badge?"
                              okText="Revoke"
                              okButtonProps={{ danger: true }}
                              cancelText="Cancel"
                              onConfirm={() => void handleRevoke(row)}
                            >
                              <Button size="small" danger type="text">
                                Revoke
                              </Button>
                            </Popconfirm>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {canManage && badge.rule_type === 'manual' && (
                <div className="mt-auto flex gap-2">
                  <Button
                    size="small"
                    icon={<GiftOutlined />}
                    onClick={() => setAwardModal({ open: true, badge })}
                  >
                    Award
                  </Button>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => setFormModal({ open: true, badge })}
                  >
                    Edit
                  </Button>
                  <Popconfirm
                    title="Delete this badge?"
                    description="All badge ownership rows will be deleted as well."
                    okText="Delete"
                    okButtonProps={{ danger: true }}
                    cancelText="Cancel"
                    onConfirm={() => void handleDelete(badge)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              )}

              {canManage && badge.rule_type !== 'manual' && (
                <div className="mt-auto flex gap-2">
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => setFormModal({ open: true, badge })}
                  >
                    Edit
                  </Button>
                  <Popconfirm
                    title="Delete this badge?"
                    description="All badge ownership rows will be deleted as well."
                    okText="Delete"
                    okButtonProps={{ danger: true }}
                    cancelText="Cancel"
                    onConfirm={() => void handleDelete(badge)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <BadgeFormModal
        open={formModal.open}
        badge={formModal.badge}
        courseId={courseId}
        onClose={() => setFormModal({ open: false, badge: null })}
        onSaved={reload}
      />
      <AwardBadgeModal
        open={awardModal.open}
        badge={awardModal.badge}
        onClose={() => setAwardModal({ open: false, badge: null })}
        onAwarded={reload}
      />
    </section>
  )
}
