import { Collapse, Empty, Skeleton, Tag } from 'antd'
import { useEffect, useState, type Key } from 'react'

import { getLeaderboardDetails, listLeaderboards, notifyError } from '@/api'
import { useAuth } from '@/auth/AuthContext'
import type { Leaderboard, LeaderboardDetailEntry } from '@/types/leaderboard'
import { fetchAllPages } from '@/utils/paginate'
import { levelColor, levelLabel } from '@/utils/level'

interface DetailState {
  status: 'loading' | 'done' | 'error'
  rows: LeaderboardDetailEntry[]
}

interface LeaderboardPanelProps {
  /** Course yang poinnya ditampilkan (satu course per panel). */
  courseId: number
}

/**
 * Papan skor satu course berbentuk Collapse per peserta — header: peringkat,
 * nama, total poin; saat expand: rincian poin per module
 * (GET /leaderboard/{id}/details/, dimuat saat pertama dibuka).
 */
export function LeaderboardPanel({ courseId }: LeaderboardPanelProps) {
  const { user } = useAuth()

  const [rows, setRows] = useState<Leaderboard[]>([])
  const [loading, setLoading] = useState(true)
  const [details, setDetails] = useState<Record<number, DetailState>>({})

  // Reset state saat ganti course (pola "adjusting state when a prop changes").
  const [prevCourseId, setPrevCourseId] = useState(courseId)
  if (prevCourseId !== courseId) {
    setPrevCourseId(courseId)
    setRows([])
    setDetails({})
    setLoading(true)
  }

  useEffect(() => {
    let cancelled = false

    fetchAllPages((params) => listLeaderboards({ ...params, course: courseId }))
      .then((items) => {
        if (!cancelled) setRows(items)
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
  }, [courseId])

  // Muat rincian saat panel dibuka; status `error` diulang saat dibuka lagi.
  const ensureDetails = (id: number) => {
    const state = details[id]
    if (state && state.status !== 'error') return
    setDetails((prev) => ({ ...prev, [id]: { status: 'loading', rows: [] } }))

    getLeaderboardDetails(id)
      .then((data) => {
        setDetails((prev) => ({ ...prev, [id]: { status: 'done', rows: data } }))
      })
      .catch((error) => {
        setDetails((prev) => ({ ...prev, [id]: { status: 'error', rows: [] } }))
        notifyError(error)
      })
  }

  const handleOpenChange = (keys: Key[]) => {
    for (const key of keys) ensureDetails(Number(key))
  }

  const renderDetail = (row: Leaderboard) => {
    const state = details[row.id]
    if (!state || state.status === 'loading') {
      return <Skeleton active paragraph={{ rows: 3 }} />
    }
    if (state.status === 'error') {
      return (
        <p className="text-sm text-red-500">
          Gagal memuat rincian poin. Buka lagi untuk mencoba kembali.
        </p>
      )
    }
    if (state.rows.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="Belum ada rincian poin untuk peserta ini."
        />
      )
    }

    return (
      <ul className="divide-y divide-gray-100">
        {state.rows.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between gap-3 py-2"
          >
            <span className="min-w-0 truncate text-sm text-gray-700">
              {item.description || 'Module'}
            </span>
            <span className="shrink-0 text-sm font-semibold text-amber-600">
              +{item.point}
            </span>
          </li>
        ))}
      </ul>
    )
  }

  if (loading) {
    return <Skeleton active paragraph={{ rows: 5 }} />
  }

  if (rows.length === 0) {
    return (
      <Empty description="Belum ada peserta yang mengumpulkan poin di course ini." />
    )
  }

  return (
    <div>
      <p className="mb-3 text-sm text-gray-500">
        {rows.length} peserta berpoin, buka salah satu untuk rincian per module.
      </p>
      <Collapse
        ghost
        className="rounded-xl border border-gray-200 bg-white"
        onChange={handleOpenChange}
        items={rows.map((row, index) => ({
          key: row.id,
          label: (
            <div className="flex items-center justify-between gap-3 pr-2">
              <span className="flex min-w-0 items-center gap-3">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    index < 3
                      ? 'bg-amber-50 text-amber-600'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {index + 1}
                </span>
                <span className="min-w-0 truncate font-medium text-[#08060d]">
                  {row.user_name}
                </span>
                <Tag color={levelColor(row.level)} className="mr-0">
                  {levelLabel(row.level, row.level_title)}
                </Tag>
                {row.user === user?.id && (
                  <Tag color="blue" className="mr-0">
                    Kamu
                  </Tag>
                )}
              </span>
              <span className="shrink-0 text-sm font-semibold text-[#08060d]">
                {row.total_points} poin
              </span>
            </div>
          ),
          children: renderDetail(row),
        }))}
      />
    </div>
  )
}
