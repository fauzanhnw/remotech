import { Empty, Pagination, Skeleton } from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { getProgressSummary, listEnrollments } from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Paginated } from '@/types/api'
import type { CourseEnrollment } from '@/types/enrollment'
import type { CourseProgressSummary } from '@/types/progress'
import { CourseCard } from '@/pages/courses/CourseCard'
import { CourseFilters } from '@/pages/courses/CourseFilters'

const PAGE_SIZE = 12

type EnrolledOrdering = 'enrolled_at' | '-enrolled_at'

const ORDER_OPTIONS: readonly { value: EnrolledOrdering; label: string }[] = [
  { value: '-enrolled_at', label: 'Terbaru' },
  { value: 'enrolled_at', label: 'Terlama' },
]

/** Daftar course yang di-enroll user — grid kartu + progress bar + pencarian. */
export function MyCoursesPage() {
  usePageTitle('Enrolled Courses')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [ordering, setOrdering] = useState<EnrolledOrdering>('-enrolled_at')
  const [page, setPage] = useState(1)

  const [enrollments, setEnrollments] = useState<Paginated<CourseEnrollment> | null>(null)
  const [summary, setSummary] = useState<CourseProgressSummary[]>([])
  const [loading, setLoading] = useState(true)

  // Debounce pencarian; reset halaman saat query berubah.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  const params = useMemo(
    () => ({
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      ordering,
    }),
    [page, search, ordering],
  )

  // Kembalikan state loading saat query berubah (pola "adjusting state when a prop changes").
  const [prevParams, setPrevParams] = useState(params)
  if (prevParams !== params) {
    setPrevParams(params)
    setLoading(true)
  }

  useEffect(() => {
    let cancelled = false

    listEnrollments(params)
      .then((data) => {
        if (!cancelled) setEnrollments(data)
      })
      .catch(() => {
        if (!cancelled) setEnrollments(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [params])

  // Ringkasan progres semua course (sekali per mount).
  useEffect(() => {
    let cancelled = false

    getProgressSummary()
      .then((rows) => {
        if (!cancelled) setSummary(rows)
      })
      .catch(() => {
        if (!cancelled) setSummary([])
      })

    return () => {
      cancelled = true
    }
  }, [])

  const handleOrderingChange = (value: EnrolledOrdering) => {
    setOrdering(value)
    setPage(1)
  }

  const progressByCourse = useMemo(
    () => new Map(summary.map((row) => [row.course, row.percent])),
    [summary],
  )

  return (
    <section className="mx-auto max-w-7xl px-4 py-10 xl:px-16 md:mx-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-[#08060d]">Enrolled Courses</h1>
        <p className="mt-2 text-gray-600">Course yang kamu ikuti beserta progres belajarmu.</p>
      </div>

      <div className="max-w">
        <CourseFilters
          search={searchInput}
          onSearchChange={setSearchInput}
          ordering={ordering}
          onOrderingChange={handleOrderingChange}
          orderOptions={ORDER_OPTIONS}
          defaultOrdering="-enrolled_at"
        />
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} active paragraph={{ rows: 4 }} />
            ))}
          </div>
        ) : !enrollments || enrollments.results.length === 0 ? (
          <Empty
            description={
              search
                ? 'Tidak ada course yang cocok.'
                : 'Kamu belum enroll course mana pun. Jelajahi katalog untuk mendaftar.'
            }
            className="py-16"
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-2 md:grid-cols-3">
              {enrollments.results.map((enrollment) => (
                <CourseCard
                  key={enrollment.id}
                  course={enrollment.course}
                  progress={progressByCourse.get(enrollment.course.id) ?? 0}
                  to={`/my-courses/${enrollment.course.id}`}
                />
              ))}
            </div>

            <div className="mt-8 flex justify-center">
              <Pagination
                current={page}
                total={enrollments.count}
                pageSize={PAGE_SIZE}
                showSizeChanger={false}
                onChange={setPage}
              />
            </div>
          </>
        )}
      </div>
    </section>
  )
}
