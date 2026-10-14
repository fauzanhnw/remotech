import { PlusCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { Button, Empty, Popconfirm, Select, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  deletePointBonus,
  listMyCourses,
  listPointBonuses,
  notifyError,
  notifySuccess,
} from '@/api'
import { LeaderboardPanel } from '@/components/LeaderboardPanel'
import { ParticipantProfileModal } from '@/components/ParticipantProfileModal'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Course } from '@/types/course'
import type { Leaderboard } from '@/types/leaderboard'
import type { PointBonus } from '@/types/pointBonus'
import { fetchAllPages } from '@/utils/paginate'
import { AddPointBonusModal } from './AddPointBonusModal'

/**
 * Leaderboard mentor: pilih salah satu course milik mentor lewat filter,
 * lalu tampilkan papan skor course itu (collapse per peserta + rincian poin).
 * Mentor bisa memberi & mencabut bonus poin manual per course.
 */
export function MentorLeaderboardPage() {
  usePageTitle('Leaderboard')

  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<number | null>(null)
  // null = modal tertutup; user terisi bila dibuka dari baris leaderboard.
  const [bonusTarget, setBonusTarget] = useState<{
    user?: number
    userName?: string
  } | null>(null)
  const [bonuses, setBonuses] = useState<PointBonus[]>([])
  const [loadingBonuses, setLoadingBonuses] = useState(false)
  // Baris leaderboard peserta yang profilnya sedang dilihat (null = tertutup).
  const [profileRow, setProfileRow] = useState<Leaderboard | null>(null)
  // Naikkan untuk memaksa panel leaderboard & riwayat reload setelah mutasi.
  const [reloadKey, setReloadKey] = useState(0)

  // Tampilkan skeleton saat ganti course / reload (pola render-time adjustment).
  const [prevBonusQuery, setPrevBonusQuery] = useState({
    selected,
    reloadKey,
  })
  if (
    prevBonusQuery.selected !== selected ||
    prevBonusQuery.reloadKey !== reloadKey
  ) {
    setPrevBonusQuery({ selected, reloadKey })
    setLoadingBonuses(true)
  }

  useEffect(() => {
    let cancelled = false

    fetchAllPages((params) => listMyCourses(params))
      .then((items) => {
        if (cancelled) return
        setCourses(items)
        setSelected(items[0]?.id ?? null)
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
  }, [])

  useEffect(() => {
    if (selected == null) return
    let cancelled = false

    fetchAllPages((params) => listPointBonuses({ ...params, course: selected }))
      .then((items) => {
        if (!cancelled) setBonuses(items)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setLoadingBonuses(false)
      })

    return () => {
      cancelled = true
    }
  }, [selected, reloadKey])

  const handleMutated = useCallback(() => {
    setReloadKey((value) => value + 1)
  }, [])

  const handleDelete = async (id: number) => {
    try {
      await deletePointBonus(id)
      notifySuccess('Point bonus revoked.')
      handleMutated()
    } catch (error) {
      notifyError(error)
    }
  }

  const options = useMemo(
    () => courses.map((course) => ({ value: course.id, label: course.title })),
    [courses],
  )

  if (loading) {
    return (
      <section className="mx-auto max-w px-4 pt-8 pb-16 md:mx-8 xl:px-16">
        <Skeleton active paragraph={{ rows: 6 }} />
      </section>
    )
  }

  if (courses.length === 0) {
    return (
      <section className="mx-auto max-w px-4 pt-8 pb-16 md:mx-8 xl:px-16">
        <Empty description="You have no courses yet. Create a course first in the Courses menu." />
      </section>
    )
  }

  return (
    <section className="mx-auto max-w px-4 pt-8 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#08060d]">Leaderboard</h2>
          <p className="mt-1 text-sm text-gray-600">
            Participant point rankings, filtered by course.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {selected != null && (
            <Button
              type="primary"
              icon={<PlusCircleOutlined />}
              onClick={() => setBonusTarget({})}
            >
              Add Manual Points
            </Button>
          )}
          <Select
            value={selected}
            onChange={setSelected}
            options={options}
            placeholder="Select course"
            style={{ width: 260 }}
            showSearch
            optionFilterProp="label"
          />
        </div>
      </div>

      {selected != null && (
        <LeaderboardPanel
          key={`${selected}-${reloadKey}`}
          courseId={selected}
          onShowProfile={setProfileRow}
          onGrantBonus={(row) =>
            setBonusTarget({ user: row.user, userName: row.user_name })
          }
        />
      )}

      {selected != null && (
        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-[#08060d]">
              Manual Point History
            </h3>
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={handleMutated}
            >
              Refresh
            </Button>
          </div>
          {loadingBonuses ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : bonuses.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="No manual point bonuses in this course yet."
            />
          ) : (
            <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 bg-white">
              {bonuses.map((bonus) => (
                <li
                  key={bonus.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[#08060d]">
                      {bonus.user_name}
                      <Tag color="green" className="ml-2 mr-0">
                        +{bonus.point} points
                      </Tag>
                    </p>
                    <p className="mt-0.5 truncate text-sm text-gray-500">
                      {bonus.description} · by {bonus.awarded_by}
                    </p>
                  </div>
                  <Popconfirm
                    title="Revoke this point bonus?"
                    okText="Revoke"
                    cancelText="Cancel"
                    onConfirm={() => void handleDelete(bonus.id)}
                  >
                    <Button danger size="small">
                      Revoke
                    </Button>
                  </Popconfirm>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {selected != null && (
        <AddPointBonusModal
          open={bonusTarget != null}
          courseId={selected}
          initialUser={bonusTarget?.user}
          onClose={() => setBonusTarget(null)}
          onGranted={handleMutated}
        />
      )}

      <ParticipantProfileModal
        open={profileRow != null}
        row={profileRow}
        onClose={() => setProfileRow(null)}
      />
    </section>
  )
}
