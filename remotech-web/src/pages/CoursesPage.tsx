import { Empty, Pagination, Skeleton } from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { listCourses } from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Paginated } from '@/types/api'
import type { Course } from '@/types/course'
import type { CourseListParams } from '@/types/params'
import { CourseCard } from './courses/CourseCard'
import { CourseFilters, type PriceFilter } from './courses/CourseFilters'

const PAGE_SIZE = 10

/** Katalog semua course terbit — grid kartu dengan search, filter, sort. */
export function CoursesPage() {
  usePageTitle('Courses')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [priceFilter, setPriceFilter] = useState<PriceFilter>('all')
  const [ordering, setOrdering] = useState<CourseListParams['ordering']>('-created_at')
  const [page, setPage] = useState(1)

  const [courses, setCourses] = useState<Paginated<Course> | null>(null)
  const [loading, setLoading] = useState(true)

  // Debounce pencarian; reset halaman saat query berubah.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  const params = useMemo<CourseListParams>(
    () => ({
      is_publish: true,
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      ordering,
      ...(priceFilter === 'free'
        ? { price__lte: 0 }
        : priceFilter === 'paid'
          ? { price__gt: 0 }
          : {}),
    }),
    [page, search, ordering, priceFilter],
  )

  // Kembalikan state loading saat query berubah (disesuaikan saat render,
  // sesuai pola React "adjusting state when a prop changes").
  const [prevParams, setPrevParams] = useState(params)
  if (prevParams !== params) {
    setPrevParams(params)
    setLoading(true)
  }

  useEffect(() => {
    let cancelled = false

    listCourses(params)
      .then((data) => {
        if (!cancelled) setCourses(data)
      })
      .catch(() => {
        if (!cancelled) setCourses(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [params])

  const handlePriceFilterChange = (value: PriceFilter) => {
    setPriceFilter(value)
    setPage(1)
  }

  const handleOrderingChange = (value: CourseListParams['ordering']) => {
    setOrdering(value)
    setPage(1)
  }

  return (
    <section className="mx-auto max-w px-4 py-10 justify-center xl:px-16 md:mx-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#08060d]">Courses</h1>
        <p className="mt-2 text-gray-600">
          Explore Remote Challenge learning materials and start your remote journey.
        </p>
      </div>

      <CourseFilters
        search={searchInput}
        onSearchChange={setSearchInput}
        priceFilter={priceFilter}
        onPriceFilterChange={handlePriceFilterChange}
        ordering={ordering}
        onOrderingChange={handleOrderingChange}
      />

      <div className="mt-6">
        {loading ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} active paragraph={{ rows: 4 }} />
            ))}
          </div>
        ) : !courses || courses.results.length === 0 ? (
          <Empty description="No courses match your search." className="py-16" />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {courses.results.map((course) => (
                <CourseCard key={course.id} course={course} />
              ))}
            </div>

            <div className="mt-8 flex justify-center">
              <Pagination
                current={page}
                total={courses.count}
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
