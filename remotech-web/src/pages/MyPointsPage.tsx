import { ReloadOutlined, TrophyOutlined } from '@ant-design/icons'
import { Button, Empty, Progress, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getMyLeaderboard, notifyError } from '@/api'
import { BadgeGrid } from '@/components/BadgeGrid'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { MyLeaderboard } from '@/types/leaderboard'
import { levelColor, levelLabel } from '@/utils/level'

/**
 * My Point: total poin dari course yang di-enroll + peringkat per course.
 * Data dari GET /leaderboard/me/ (rank null bila belum pernah menyelesaikan module).
 */
export function MyPointsPage() {
  usePageTitle('My Point')

  const [data, setData] = useState<MyLeaderboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(() => {
    setLoading(true)
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    getMyLeaderboard()
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((error) => {
        if (cancelled) return
        setData(null)
        notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [reloadKey])

  if (!data && loading) {
    return (
      <section className="mx-auto max-w px-4 py-10 pb-16 md:mx-8 xl:px-16">
        <h1 className="mb-6 text-3xl font-bold text-[#08060d]">My Point</h1>
        <Skeleton active paragraph={{ rows: 6 }} />
      </section>
    )
  }

  if (!data) {
    return (
      <section className="mx-auto max-w px-4 py-10 pb-16 md:mx-8 xl:px-16">
        <h1 className="mb-6 text-3xl font-bold text-[#08060d]">My Point</h1>
        <Empty description="Failed to load points data." className="py-16">
          <Button type="primary" onClick={() => void load()}>
            Try again
          </Button>
        </Empty>
      </section>
    )
  }

  const courseCount = data.courses.length
  const hasPoints = data.total_points > 0
  const isMaxLevel = data.next_level_title == null

  return (
    <section className="mx-auto max-w px-4 py-10 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#08060d]">My Point</h1>
          <p className="mt-2 text-gray-600">
            Accumulated points from the courses you have taken.
          </p>
        </div>
        <Button
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={() => void load()}
        >
          Refresh
        </Button>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-4">
          <span className="mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-amber-50">
            <TrophyOutlined className="text-2xl text-amber-500" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-2">
              <p className="text-3xl font-bold leading-none text-[#08060d]">
                {data.total_points}
              </p>
              <Tag color={levelColor(data.level)} className="mr-0">
                {levelLabel(data.level, data.level_title)}
              </Tag>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Total points from {courseCount} courses
            </p>
          </div>
        </div>
        <div className="mt-4">
          {isMaxLevel ? (
            <p className="text-sm font-medium text-amber-600">
              Max level reached — you are already Master!
            </p>
          ) : (
            <>
              <Progress
                percent={data.level_progress}
                strokeColor={{ '0%': '#1677ff', '100%': '#722ed1' }}
                showInfo={false}
              />
              <p className="mt-1 text-sm text-gray-500">
                {' '}
                <span className="font-semibold text-[#08060d]">
                  {data.points_to_next_level}
                </span>{' '}
                more points to reach level{' '}
                <span className="font-semibold text-[#08060d]">
                  {data.next_level_title}
                </span>
              </p>
            </>
          )}
        </div>
      </div>

      {!hasPoints && (
        <p className="mb-4 text-sm text-gray-500">
          Complete modules (read the material, submit assignments, take quizzes) to
          start collecting points.
        </p>
      )}

      {courseCount === 0 ? (
        <Empty
          description="You haven't enrolled in any courses yet. Browse the catalog to sign up."
          className="py-16"
        >
          <Link to="/courses" className="inline-flex">
            <Button type="primary">Browse Catalog</Button>
          </Link>
        </Empty>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.courses.map((row) => (
            <Link
              key={row.course}
              to={`/my-courses/${row.course}`}
              className="group rounded-xl border border-gray-200 bg-white p-4 no-underline shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <p className="truncate text-base font-semibold text-[#08060d]">
                {row.course_title}
              </p>
              <div className="mt-3 flex items-end justify-between gap-2">
                <div>
                  <p className="text-2xl font-bold leading-none text-[#08060d]">
                    {row.total_points}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">points</p>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    row.rank == null
                      ? 'bg-gray-100 text-gray-600'
                      : 'bg-amber-50 text-amber-600'
                  }`}
                >
                  {row.rank == null
                    ? 'No points yet'
                    : `#${row.rank} of ${row.participants} participants`}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <div className="mt-10">
        <h2 className="mb-1 text-xl font-bold text-[#08060d]">Badge</h2>
        <p className="mb-4 text-sm text-gray-600">
          Collect badges from the courses you have taken — complete all modules
          or earn awards from your mentor.
        </p>
        <BadgeGrid showCourse />
      </div>
    </section>
  )
}
