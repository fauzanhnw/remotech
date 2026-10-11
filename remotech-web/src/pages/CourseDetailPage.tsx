import { PictureOutlined } from '@ant-design/icons'
import { Button, Empty, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import {
  checkPayment,
  enrollCourse,
  getCourse,
  isApiError,
  listBadges,
  listEnrollments,
  listModules,
  notifyError,
  notifySuccess,
  notifyWarning,
  payWithSnap,
} from '@/api'
import { useAuth } from '@/auth/AuthContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { BadgeCard } from '@/components/BadgeCard'
import type { Badge } from '@/types/badge'
import type { Course, CourseModule } from '@/types/course'
import { formatRupiah } from '@/utils/format'
import { ModuleAccordion } from './courses/ModuleAccordion'

/** Detail course: hero (thumbnail + info + enroll), deskripsi, daftar module. */
export function CourseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, user } = useAuth()

  const [course, setCourse] = useState<Course | null>(null)
  const [modules, setModules] = useState<CourseModule[]>([])
  const [badges, setBadges] = useState<Badge[]>([])
  const [enrolled, setEnrolled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [acting, setActing] = useState(false)

  const invalidId = !Number.isInteger(courseId) || courseId <= 0

  // Sinkronisasi state saat id/user berubah (disesuaikan saat render, bukan di effect).
  const [prevCourseId, setPrevCourseId] = useState(courseId)
  if (prevCourseId !== courseId) {
    setPrevCourseId(courseId)
    setLoading(true)
    setLoadFailed(false)
    setNotFound(false)
    setBadges([])
  }
  const [prevUser, setPrevUser] = useState(user)
  if (prevUser !== user) {
    setPrevUser(user)
    setEnrolled(false)
  }

  usePageTitle(course?.title)

  // Muat course + module.
  useEffect(() => {
    if (invalidId) return

    let cancelled = false

    Promise.all([getCourse(courseId), listModules({ course: courseId, page_size: 100 })])
      .then(([fetchedCourse, modulePage]) => {
        if (cancelled) return
        setCourse(fetchedCourse)
        setModules(modulePage.results)
      })
      .catch((error) => {
        if (cancelled) return
        if (isApiError(error) && error.status === 404) setNotFound(true)
        else setLoadFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, invalidId])

  // Muat daftar badge course (publik) — gagal diam-diam, section disembunyikan.
  useEffect(() => {
    if (invalidId) return

    let cancelled = false
    listBadges({ course: courseId, page_size: 100 })
      .then((page) => {
        if (!cancelled) setBadges(page.results)
      })
      .catch(() => {
        if (!cancelled) setBadges([])
      })

    return () => {
      cancelled = true
    }
  }, [courseId, invalidId])

  const refreshEnrollment = useCallback(async () => {
    if (!isAuthenticated || !user) return
    try {
      const data = await listEnrollments({ course: courseId, user: user.id, page_size: 1 })
      setEnrolled(data.results.length > 0)
    } catch {
      setEnrolled(false)
    }
  }, [courseId, isAuthenticated, user])

  useEffect(() => {
    if (!isAuthenticated || !user) return
    let cancelled = false
    listEnrollments({ course: courseId, user: user.id, page_size: 1 })
      .then((data) => {
        if (!cancelled) setEnrolled(data.results.length > 0)
      })
      .catch(() => {
        if (!cancelled) setEnrolled(false)
      })
    return () => {
      cancelled = true
    }
  }, [courseId, isAuthenticated, user])

  const handleEnroll = async () => {
    if (!course) return
    setActing(true)
    try {
      const result = await enrollCourse(course.id)

      if (result.enrolled) {
        void refreshEnrollment()
        notifySuccess('Berhasil enroll. Selamat belajar!')
        return
      }

      if (result.snap_token) {
        const snapResult = await payWithSnap(result.snap_token)
        const order = await checkPayment(result.order.id)

        if (order.transaction_status === 'settlement') {
          void refreshEnrollment()
          notifySuccess('Pembayaran berhasil! Course sudah masuk ke daftar belajarmu.')
        } else if (snapResult.status === 'error') {
          notifyError('Pembayaran gagal. Silakan coba lagi.')
        } else {
          notifyWarning(
            `Pembayaran masih berstatus "${order.transaction_status}". Silakan periksa kembali nanti.`,
          )
        }
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setActing(false)
    }
  }

  const handlePrimaryClick = () => {
    if (enrolled) {
      navigate(course ? `/my-courses/${course.id}` : '/my-courses')
      return
    }
    if (!isAuthenticated) {
      navigate('/login', { state: { from: location.pathname } })
      return
    }
    void handleEnroll()
  }

  if (invalidId || notFound) return <NotFoundPage />

  if (loading) {
    return (
      <section className="mx-auto max-w-6xl px-4 py-10">
        <Skeleton active paragraph={{ rows: 8 }} />
      </section>
    )
  }

  if (loadFailed || !course) {
    return (
      <section className="mx-auto max-w-6xl px-4 py-16">
        <Empty description="Gagal memuat course. Silakan coba lagi." />
      </section>
    )
  }

  const isClosed = !course.is_open && !enrolled
  const buttonLabel = enrolled
    ? 'Lanjutkan Belajar'
    : course.price <= 0
      ? 'Enroll Gratis'
      : 'Beli Sekarang'

  return (
    <>
      {/* Section 1: thumbnail, judul, uploader, harga, aksi */}
      <section className="border-b border-gray-200 bg-gray-50">
        <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-10 md:grid-cols-2">
          <div className="aspect-video overflow-hidden rounded-xl border border-gray-200 bg-white">
            {course.thumbnail ? (
              <img
                src={course.thumbnail}
                alt={course.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-5xl text-gray-300">
                <PictureOutlined />
              </div>
            )}
          </div>

          <div>
            <Tag color={course.is_open ? 'green' : 'red'}>
              {course.is_open ? 'Pendaftaran Dibuka' : 'Pendaftaran Ditutup'}
            </Tag>
            <h1 className="mt-3 text-3xl font-bold text-[#08060d] md:text-3xl lg:text-4xl">
              {course.title}
            </h1>
            <p className="mt-2 text-gray-600">By {course.user_name}</p>
            <p className="mt-4 text-2xl font-bold text-[#08060d]">
              {formatRupiah(course.price)}
            </p>

            <Button
              type="primary"
              size="large"
              className="mt-3 min-w-48 font-medium"
              loading={acting}
              disabled={isClosed}
              onClick={handlePrimaryClick}
            >
              {buttonLabel}
            </Button>

            {isClosed && (
              <p className="mt-3 text-sm text-red-500">
                Pendaftaran course ini sedang ditutup.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* Section 2: deskripsi */}
      <section className="mx-auto max-w-6xl px-4 py-10">
        <h2 className="text-2xl font-bold text-[#08060d]">Deskripsi</h2>
        <p className="mt-4 whitespace-pre-line leading-relaxed text-gray-600">
          {course.description || 'Belum ada deskripsi untuk course ini.'}
        </p>
      </section>

      {/* Section 2b: badge yang bisa didapatkan di course ini */}
      {badges.length > 0 && (
        <section className="mx-auto max-w-6xl px-4 pb-10">
          <h2 className="text-2xl font-bold text-[#08060d]">Badge Course</h2>
          <p className="mt-1 text-sm text-gray-600">
            Badge yang bisa kamu dapatkan setelah menyelesaikan course ini.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {badges.map((badge) => (
              <BadgeCard key={badge.id} badge={badge} earned={false} />
            ))}
          </div>
        </section>
      )}

      {/* Section 3: daftar module */}
      <section className="mx-auto max-w-6xl px-4 pb-16">
        <h2 className="text-2xl font-bold text-[#08060d]">Course Modules</h2>
        <div className="mt-4">
          {modules.length > 0 ? (
            <ModuleAccordion modules={modules} />
          ) : (
            <Empty description="Belum ada module untuk course ini." />
          )}
        </div>
      </section>
    </>
  )
}
