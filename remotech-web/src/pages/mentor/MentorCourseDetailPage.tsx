import { EditOutlined, PictureOutlined, DeleteOutlined } from '@ant-design/icons'
import { Button, Empty, Popconfirm, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { deleteCourse, getCourse, isApiError, notifyError, notifySuccess } from '@/api'
import { useAuth } from '@/auth/AuthContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import { NotFoundPage } from '@/pages/NotFoundPage'
import type { Course } from '@/types/course'
import { formatRupiah } from '@/utils/format'
import { EditCourseModal } from './EditCourseModal'
import { ModuleSection } from './ModuleSection'

/** Detail course untuk mentor: edit/hapus course + kelola module & konten. */
export function MentorCourseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)
  const navigate = useNavigate()
  const { user } = useAuth()

  const [course, setCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const invalidId = !Number.isInteger(courseId) || courseId <= 0

  // Sinkronisasi state saat id berubah (disesuaikan saat render).
  const [prevCourseId, setPrevCourseId] = useState(courseId)
  if (prevCourseId !== courseId) {
    setPrevCourseId(courseId)
    setLoading(true)
    setLoadFailed(false)
    setNotFound(false)
  }

  const loadCourse = useCallback(() => {
    if (invalidId) return
    let cancelled = false

    getCourse(courseId)
      .then((data) => {
        if (cancelled) return
        setCourse(data)
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

  useEffect(() => loadCourse(), [loadCourse])

  usePageTitle(course?.title)

  const handleDelete = async () => {
    if (!course) return
    setDeleting(true)
    try {
      await deleteCourse(course.id)
      notifySuccess('Course berhasil dihapus.')
      navigate('/mentor/courses')
    } catch (error) {
      notifyError(error)
    } finally {
      setDeleting(false)
    }
  }

  if (invalidId || notFound) return <NotFoundPage />

  if (loading) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-10 md:mx-8 xl:px-16">
        <Skeleton active paragraph={{ rows: 8 }} />
      </section>
    )
  }

  if (loadFailed || !course) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-16 md:mx-8 xl:px-16">
        <Empty description="Gagal memuat course. Silakan coba lagi." />
      </section>
    )
  }

  const isOwner = user?.id === course.user

  return (
    <>
      {/* Section 1: thumbnail, status, harga, aksi kelola */}
      <section className="border-b border-gray-200 bg-gray-50">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-4 py-10 md:mx-8 md:grid-cols-2 xl:px-16">
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
            <div className="flex flex-wrap gap-2">
              <Tag color={course.is_publish ? 'blue' : 'default'}>
                {course.is_publish ? 'Published' : 'Draft'}
              </Tag>
              <Tag color={course.is_open ? 'green' : 'red'}>
                {course.is_open ? 'Pendaftaran Dibuka' : 'Pendaftaran Ditutup'}
              </Tag>
            </div>

            <h1 className="mt-3 text-3xl font-bold text-[#08060d] lg:text-4xl">
              {course.title}
            </h1>
            <p className="mt-2 text-gray-600">oleh {course.user_name}</p>
            <p className="mt-4 text-2xl font-bold text-[#08060d]">
              {formatRupiah(course.price)}
            </p>

            <div className="mt-4 flex flex-wrap gap-3">
              {isOwner && (
                <Button
                  type="primary"
                  size="large"
                  className="min-w-40 font-medium"
                  icon={<EditOutlined />}
                  onClick={() => setEditOpen(true)}
                >
                  Edit Course
                </Button>
              )}

              <Link
                to={`/courses/${course.id}`}
                className="inline-flex"
                aria-label="Preview halaman publik"
              >
                <Button size="large">Preview</Button>
              </Link>

              {isOwner && (
                <Popconfirm
                  title="Hapus course ini?"
                  description="Semua module, konten, enrollment, dan order terkait ikut terhapus permanen."
                  okText="Hapus"
                  okButtonProps={{ danger: true }}
                  cancelText="Batal"
                  onConfirm={() => void handleDelete()}
                >
                  <Button
                    size="large"
                    danger
                    loading={deleting}
                    icon={<DeleteOutlined />}
                  >
                    Delete
                  </Button>
                </Popconfirm>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: deskripsi */}
      <section className="mx-auto max-w-7xl px-4 py-10 md:mx-8 xl:px-16">
        <h2 className="text-2xl font-bold text-[#08060d]">Deskripsi</h2>
        <p className="mt-4 whitespace-pre-line leading-relaxed text-gray-600">
          {course.description || 'Belum ada deskripsi untuk course ini.'}
        </p>
      </section>

      {/* Section 3: kelola module & konten */}
      <ModuleSection courseId={course.id} canManage={isOwner} />

      <EditCourseModal
        open={editOpen}
        course={course}
        onClose={() => setEditOpen(false)}
        onSaved={loadCourse}
      />
    </>
  )
}
