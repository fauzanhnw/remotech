import { PlusOutlined } from '@ant-design/icons'
import { Button, Empty, Pagination, Skeleton } from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { listMyCourses } from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Paginated } from '@/types/api'
import type { Course } from '@/types/course'
import type { CourseListParams } from '@/types/params'
import { CourseCard } from '@/pages/courses/CourseCard'
import { CourseFilters, type PriceFilter } from '@/pages/courses/CourseFilters'
import { AddCourseModal } from './AddCourseModal'

const PAGE_SIZE = 12

/** Daftar course milik mentor (termasuk draft) — grid kartu + pencarian + Add Course. */
export function MentorCoursesPage() {
  usePageTitle('My Courses')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [priceFilter, setPriceFilter] = useState<PriceFilter>('all')
  const [ordering, setOrdering] = useState<CourseListParams['ordering']>('-created_at')
  const [page, setPage] = useState(1)
  const [refreshKey, setRefreshKey] = useState(0)
  const [modalOpen, setModalOpen] = useState(false)

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

  // Kembalikan state loading saat query berubah (pola "adjusting state when a prop changes").
  const [prevParams, setPrevParams] = useState(params)
  if (prevParams !== params) {
    setPrevParams(params)
    setLoading(true)
  }

  useEffect(() => {
    let cancelled = false

    listMyCourses(params)
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
  }, [params, refreshKey])

  const handleCreated = () => {
    setPage(1)
    setRefreshKey((value) => value + 1)
  }

  const handlePriceFilterChange = (value: PriceFilter) => {
    setPriceFilter(value)
    setPage(1)
  }

  const handleOrderingChange = (value: CourseListParams['ordering']) => {
    setOrdering(value)
    setPage(1)
  }

  return (
    <section className="mx-auto max-w px-4 py-10 xl:px-16 md:mx-8">
      <div className="mb flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#08060d]">My Courses</h1>
          <p className="mt-2 text-gray-600">
            Manage Courses
          </p>
        </div>

        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          className="mb-3"
          onClick={() => setModalOpen(true)}
        >
          Add Course
        </Button>
      </div>

      <div className="max-w">
        <CourseFilters
          search={searchInput}
          onSearchChange={setSearchInput}
          priceFilter={priceFilter}
          onPriceFilterChange={handlePriceFilterChange}
          ordering={ordering}
          onOrderingChange={handleOrderingChange}
        />
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} active paragraph={{ rows: 4 }} />
            ))}
          </div>
        ) : !courses || courses.results.length === 0 ? (
          <Empty
            description={
              search
                ? 'No courses match.'
                : 'No courses yet. Click Add Course to create your first course.'
            }
            className="py-16"
          />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {courses.results.map((course) => (
                <CourseCard
                  key={course.id}
                  course={course}
                  to={`/mentor/courses/${course.id}`}
                />
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

      <AddCourseModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={handleCreated} />
    </section>
  )
}
