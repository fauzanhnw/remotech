import { Empty, Select, Skeleton } from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { listMyCourses, notifyError } from '@/api'
import { LeaderboardPanel } from '@/components/LeaderboardPanel'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Course } from '@/types/course'
import { fetchAllPages } from '@/utils/paginate'

/**
 * Leaderboard mentor: pilih salah satu course milik mentor lewat filter,
 * lalu tampilkan papan skor course itu (collapse per peserta + rincian poin).
 */
export function MentorLeaderboardPage() {
  usePageTitle('Leaderboard')

  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<number | null>(null)

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
        <Empty description="Belum ada course milikmu. Buat course dulu di menu Courses." />
      </section>
    )
  }

  return (
    <section className="mx-auto max-w px-4 pt-8 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#08060d]">Leaderboard</h2>
          <p className="mt-1 text-sm text-gray-600">
            Peringkat poin peserta — pilih course untuk melihat papan skornya.
          </p>
        </div>
        <Select
          value={selected}
          onChange={setSelected}
          options={options}
          placeholder="Pilih course"
          style={{ width: 260 }}
          showSearch
          optionFilterProp="label"
        />
      </div>

      {selected != null && <LeaderboardPanel key={selected} courseId={selected} />}
    </section>
  )
}
