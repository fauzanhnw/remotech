import {
  ArrowLeftOutlined,
  CheckCircleFilled,
  CheckOutlined,
  ExpandOutlined,
  LinkOutlined,
  PictureOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { Button, Drawer, Empty, Modal, Skeleton, Tabs, Tag, Tooltip } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getCourse,
  isApiError,
  listContentViewed,
  listEnrollments,
  listModuleContents,
  listModules,
  listProgress,
  markContentViewed,
  markModuleComplete,
  notifyError,
  unmarkProgress,
} from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import { NotFoundPage } from '@/pages/NotFoundPage'
import type { ModuleContent } from '@/types/content'
import type { Course, CourseModule } from '@/types/course'
import type { CourseEnrollment } from '@/types/enrollment'
import type { UserProgress } from '@/types/progress'
import { isDirectVideo, toEmbedUrl } from '@/utils/video'
import { AssignmentSubmitPanel } from './AssignmentSubmitPanel'
import { CurriculumList } from './CurriculumList'

const IMAGE_URL = /\.(png|jpe?g|gif|webp|avif|svg)(\?.*)?$/i

/** Styling HTML teks — `content_text` sudah disanitasi backend (whitelist nh3). */
const TEXT_HTML_CLASS =
  '[&_img]:my-3 [&_img]:max-h-full [&_img]:max-w-full [&_img]:h-auto [&_img]:rounded-md [&_img]:border [&_img]:border-gray-200 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-6'

interface SelectedPreview {
  module: CourseModule
  /** Null bila module dipilih langsung (module `upload` tanpa konten). */
  content: ModuleContent | null
}

/** Detail course yang di-enroll: player pratinjau + detail + kurikulum (gaya Udemy). */
export function EnrolledCourseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)

  const [course, setCourse] = useState<Course | null>(null)
  const [modules, setModules] = useState<CourseModule[]>([])
  const [enrollment, setEnrollment] = useState<CourseEnrollment | null>(null)
  const [progressRows, setProgressRows] = useState<UserProgress[]>([])
  const [viewedContentIds, setViewedContentIds] = useState<Set<number>>(new Set())
  const [selected, setSelected] = useState<SelectedPreview | null>(null)
  const [busyModuleId, setBusyModuleId] = useState<number | null>(null)

  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [notEnrolled, setNotEnrolled] = useState(false)

  // Terbuka otomatis saat masuk halaman (hanya dirender di xl — mode dorong).
  const [drawerOpen, setDrawerOpen] = useState(true)
  const [fullViewOpen, setFullViewOpen] = useState(false)
  // Kurikulum: sidebar geser dari kanan hanya di xl (≥1280px); di bawah itu tabs.
  const [isXl, setIsXl] = useState(() =>
    window.matchMedia('(min-width: 1280px)').matches,
  )

  const invalidId = !Number.isInteger(courseId) || courseId <= 0

  // Sinkronisasi state saat id berubah (disesuaikan saat render).
  const [prevCourseId, setPrevCourseId] = useState(courseId)
  if (prevCourseId !== courseId) {
    setPrevCourseId(courseId)
    setCourse(null)
    setModules([])
    setEnrollment(null)
    setProgressRows([])
    setViewedContentIds(new Set())
    setSelected(null)
    setLoading(true)
    setLoadFailed(false)
    setNotFound(false)
    setNotEnrolled(false)
    setDrawerOpen(true)
    setFullViewOpen(false)
  }

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)')
    const handler = (event: MediaQueryListEvent) => {
      setIsXl(event.matches)
      // Drawer kurikulum hanya valid di xl — tutup saat turun di bawah xl.
      if (!event.matches) setDrawerOpen(false)
    }
    media.addEventListener('change', handler)
    return () => media.removeEventListener('change', handler)
  }, [])

  // Sidebar kurikulum (xl): saat terbuka, seluruh shell ikut terdorong
  // seukuran drawer (lihat aturan `.curriculum-pushed` di index.css).
  useEffect(() => {
    document.documentElement.classList.toggle('curriculum-pushed', isXl && drawerOpen)
    return () => {
      document.documentElement.classList.remove('curriculum-pushed')
    }
  }, [isXl, drawerOpen])

  // Boot: course + module + enrollment (gagal → fallback; belum enroll → Empty).
  useEffect(() => {
    if (invalidId) return
    let cancelled = false

    Promise.all([
      getCourse(courseId),
      listModules({ course: courseId, page_size: 100 }),
      listEnrollments({ course: courseId, page_size: 1 }),
    ])
      .then(([courseData, modulePage, enrollmentPage]) => {
        if (cancelled) return
        if (enrollmentPage.results.length === 0) {
          setNotEnrolled(true)
          return
        }
        setCourse(courseData)
        setModules(modulePage.results)
        setEnrollment(enrollmentPage.results[0])
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

  // Progres per module milik sendiri (gagal → diam, semua 0%).
  useEffect(() => {
    if (invalidId) return
    let cancelled = false

    listProgress({ course: courseId, page_size: 100 })
      .then((page) => {
        if (!cancelled) setProgressRows(page.results)
      })
      .catch(() => {
        // diabaikan — kartu tetap tampil dengan progres 0
      })

    return () => {
      cancelled = true
    }
  }, [courseId, invalidId])

  // Id konten yang sudah dibuka (untuk centang di kurikulum).
  useEffect(() => {
    if (invalidId) return
    let cancelled = false

    listContentViewed({ course: courseId })
      .then((data) => {
        if (!cancelled) setViewedContentIds(new Set(data.content_ids))
      })
      .catch(() => {
        // diabaikan — centang hanya fitur tampilan
      })

    return () => {
      cancelled = true
    }
  }, [courseId, invalidId])

  const sortedModules = useMemo(
    () =>
      [...modules].sort(
        (a, b) =>
          (a.sequence ?? Number.MAX_SAFE_INTEGER) - (b.sequence ?? Number.MAX_SAFE_INTEGER),
      ),
    [modules],
  )

  // Pratinjau awal: konten pertama dari module pertama yang punya konten.
  useEffect(() => {
    if (selected !== null || sortedModules.length === 0) return
    let cancelled = false

    void (async () => {
      for (const module of sortedModules) {
        let page
        try {
          page = await listModuleContents({ module: module.id, page_size: 100 })
        } catch {
          return
        }
        if (cancelled) return
        if (page.results.length > 0) {
          setSelected({ module, content: page.results[0] })
          return
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [sortedModules, selected])

  const progressIdByModule = useMemo(() => {
    const map = new Map<number, number>()
    for (const row of progressRows) map.set(row.module, row.id)
    return map
  }, [progressRows])

  const completedIds = useMemo(
    () =>
      new Set(
        progressRows.filter((row) => row.status === 'finish').map((row) => row.module),
      ),
    [progressRows],
  )

  // Auto-complete: setiap buka konten ditandai lewat backend; module text/video
  // baru selesai saat SEMUA kontennya sudah dilihat (POST /content-view/),
  // bukan konten pertama. Gagal → diam; manual tetap bisa lewat kurikulum.
  useEffect(() => {
    const content = selected?.content
    if (!content) return

    markContentViewed(content.id, { meta: { suppressErrorToast: true } })
      .then((result) => {
        setViewedContentIds((prev) => {
          if (prev.has(content.id)) return prev
          const next = new Set(prev)
          next.add(content.id)
          return next
        })
        if (result.module_completed) {
          listProgress({ course: courseId, page_size: 100 })
            .then((page) => setProgressRows(page.results))
            .catch(() => {
              // diabaikan
            })
        }
      })
      .catch(() => {
        // diabaikan — student masih bisa menandai manual lewat kurikulum
      })
  }, [selected?.content, courseId])

  const handleToggleComplete = async (module: CourseModule) => {
    const isDone = completedIds.has(module.id)
    const progressId = progressIdByModule.get(module.id)

    setBusyModuleId(module.id)
    try {
      if (isDone && progressId != null) {
        await unmarkProgress(progressId)
        setProgressRows((prev) => prev.filter((row) => row.module !== module.id))
      } else {
        const row = await markModuleComplete(module.id)
        setProgressRows((prev) => [
          ...prev.filter((item) => item.module !== module.id),
          row,
        ])
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setBusyModuleId(null)
    }
  }

  const handleSelectContent = (module: CourseModule, content: ModuleContent) => {
    setSelected({ module, content })
    setDrawerOpen(false)
    setFullViewOpen(false)
  }

  const handleSelectModule = (module: CourseModule) => {
    setSelected({ module, content: null })
    setDrawerOpen(false)
    setFullViewOpen(false)
  }

  // Muat ulang progres setelah submit tugas (backend menandai module selesai).
  const refreshProgress = () => {
    listProgress({ course: courseId, page_size: 100 })
      .then((page) => setProgressRows(page.results))
      .catch(() => {
        // diabaikan
      })
  }

  const handleToggleCurriculum = () => setDrawerOpen((value) => !value)

  usePageTitle(course?.title)

  if (invalidId || notFound) return <NotFoundPage />

  if (loading) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-10 md:mx-8 xl:px-16">
        <Skeleton active paragraph={{ rows: 8 }} />
      </section>
    )
  }

  if (notEnrolled) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-16 md:mx-8 xl:px-16">
        <Empty description="Kamu belum enroll course ini.">
          <Link to="/courses" className="inline-flex">
            <Button type="primary">Jelajahi Katalog</Button>
          </Link>
        </Empty>
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

  const selectedDone = selected ? completedIds.has(selected.module.id) : false
  const showFullViewButton =
    selected?.module.module_category === 'text' &&
    !!selected.content?.content_text.trim()

  const renderLinkCard = (url: string, label: string) => (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <LinkOutlined className="text-4xl text-gray-400" />
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="break-all text-sm text-blue-400 no-underline hover:underline"
      >
        {label}
      </a>
      <p className="break-all text-xs text-gray-500">{url}</p>
    </div>
  )

  const renderPreview = () => {
    if (!selected) {
      return course.thumbnail ? (
        <img
          src={course.thumbnail}
          alt={course.title}
          className="h-full w-full object-cover opacity-70"
        />
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-500">
          <PictureOutlined className="text-5xl" />
          <p className="text-sm">Pratinjau konten belum tersedia.</p>
        </div>
      )
    }

    const { module, content } = selected

    if (module.module_category === 'upload') {
      return (
        <div className="h-full overflow-y-auto overscroll-contain bg-white p-4 sm:p-6 md:p-10">
          <AssignmentSubmitPanel
            key={module.id}
            module={module}
            onSubmitted={refreshProgress}
          />
          {content?.content_text.trim() && (
            <div
              className={`w-full h-auto mt-6 border-t border-gray-200 pt-4 text-[#08060d] ${TEXT_HTML_CLASS}`}
            >
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                {/* Instruksi dari mentor */}
              </p>
              {/* content_text sudah disanitasi backend (whitelist nh3). */}
              <div dangerouslySetInnerHTML={{ __html: content.content_text }} />
            </div>
          )}
          {content?.content_url && (
            <a
              href={content.content_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center gap-2 text-sm text-blue-600 no-underline hover:underline"
            >
              <LinkOutlined /> Lampiran dari mentor
            </a>
          )}
        </div>
      )
    }

    if (!content) {
      return (
        <div className="flex h-full items-center justify-center p-6 text-center text-sm text-gray-400">
          Tidak ada isi untuk konten ini.
        </div>
      )
    }

    const url = content.content_url

    if (url && module.module_category === 'video') {
      const embed = toEmbedUrl(url)
      if (embed) {
        return (
          <iframe
            title="Video pembelajaran"
            src={embed}
            allowFullScreen
            className="h-full w-full border-0"
          />
        )
      }
      if (isDirectVideo(url)) {
        return <video src={url} controls playsInline className="h-full w-full bg-black" />
      }
      return renderLinkCard(url, 'Buka video')
    }

    if (content.content_text.trim()) {
      // content_text sudah disanitasi backend (whitelist nh3) — aman dirender.
      return (
        <div
          className={`h-full overflow-y-auto overscroll-contain bg-white p-4 text-[#08060d] sm:p-6 md:p-10 ${TEXT_HTML_CLASS}`}
          dangerouslySetInnerHTML={{ __html: content.content_text }}
        />
      )
    }

    if (url) {
      if (IMAGE_URL.test(url)) {
        return <img src={url} alt="" className="h-full w-full bg-white object-contain" />
      }
      return renderLinkCard(
        url,
        module.module_category === 'video' ? 'Buka video' : 'Buka dokumen',
      )
    }

    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm text-gray-400">
        {module.module_category === 'quiz'
          ? 'Module ini berupa kuis.'
          : 'Tidak ada isi untuk konten ini.'}
      </div>
    )
  }

  const curriculumList = (
    <CurriculumList
      key={courseId}
      modules={sortedModules}
      completedIds={completedIds}
      viewedContentIds={viewedContentIds}
      busyModuleId={busyModuleId}
      selectedContentId={selected?.content?.id ?? null}
      selectedModuleId={selected?.module.id ?? null}
      onToggleComplete={(module) => void handleToggleComplete(module)}
      onSelectContent={handleSelectContent}
      onSelectModule={handleSelectModule}
    />
  )

  // Gambaran umum course — dipakai di cabang xl (langsung) dan tab <xl.
  const overviewContent = (
    <div className="min-w-0">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-black md:text-3xl">{course.title}</h1>
        <p className="mt-1 text-sm text-gray-600">By: {course.user_name}</p>
        {selected && (
          <p className="mt-2 text-sm text-gray-500">Module: {selected.module.title}</p>
        )}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Tag color={course.is_open ? 'green' : 'red'}>
          {course.is_open ? 'Registration Open' : 'Registration Closed'}
        </Tag>
        <Tag color="blue">{course.is_publish ? 'Published' : 'Draft'}</Tag>
        {enrollment && (
          <Tag>
            Enrolled at{' '}
            {new Date(enrollment.enrolled_at).toLocaleDateString('id-ID', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </Tag>
        )}
      </div>

      <h2 className="mt-6 text-2xl font-bold text-[#08060d]">Deskripsi</h2>
      <p className="mt-4 whitespace-pre-line leading-relaxed text-gray-600">
        {course.description || 'Belum ada deskripsi untuk course ini.'}
      </p>
    </div>
  )

  return (
    <>
      {/* Section atas (full-bleed gelap): toolbar + player pratinjau + judul + aksi */}
      <section className="">
        <div className="mx-auto max-w pb-1">
          <div className="flex items-center justify-between gap-3 px-4 py-3 sm:gap-4 xl:px-5 bg-[#111827]">
            <Link
              to="/my-courses"
              className="flex min-w-0 items-center gap-2 text-sm text-gray-300 no-underline hover:text-white"
            >
              <ArrowLeftOutlined className="shrink-0" />
              <span className="truncate font-semibold ms-3">{course.title}</span>
            </Link>
            {isXl && (
              <Tooltip title="View Content" placement="bottom">
                <Button
                  icon={<UnorderedListOutlined />}
                  onClick={handleToggleCurriculum}
                />
              </Tooltip>
            )}
          </div>

          <div className="aspect-video overflow-hidden bg-black w-full min-h-[350px] sm:max-h-[350px] md:max-h-[380px]">
            {renderPreview()}
          </div>

          <div className="my-1 flex flex-wrap items-start justify-end gap-4 px-4">
            {showFullViewButton && (
              <Tooltip title="View Full" placement="topLeft">
                <Button
                className="w-full sm:w-auto"
                icon={<ExpandOutlined />}
                onClick={() => setFullViewOpen(true)}
                >
                </Button>
              </Tooltip>
              
            )}
            {selected && selected.module.module_category === 'quiz' && (
              <Button
                type={selectedDone ? 'default' : 'primary'}
                className="w-full sm:w-auto"
                icon={selectedDone ? <CheckCircleFilled /> : <CheckOutlined />}
                loading={busyModuleId === selected.module.id}
                onClick={() => void handleToggleComplete(selected.module)}
              >
                {selectedDone ? 'Sudah selesai' : 'Tandai selesai'}
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* Section bawah: xl = gambaran umum (kurikulum di drawer kanan);
          <xl = tabs Kurikulum | Gambaran Umum */}
      <section className="mx-auto max-w-7xl border-t px-4 py-6 md:mx-8 md:py-10 xl:px-16">
        {isXl ? (
          overviewContent
        ) : (
          <Tabs
            items={[
              { key: 'kurikulum', label: 'Kurikulum', children: curriculumList },
              { key: 'overview', label: 'Gambaran Umum', children: overviewContent },
            ]}
          />
        )}
      </section>

      {isXl && (
        <Drawer
          placement="right"
          width="min(384px, 100vw)"
          // Mode dorong (push): tanpa mask — konten ikut menggeser, tutup via
          // tombol X / Esc / tombol toolbar.
          mask={false}
          styles={{ body: { padding: 0 } }}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          {curriculumList}
        </Drawer>
      )}

      {/* Bacaan penuh konten text — layar lebar dengan scroll nyaman. */}
      <Modal
        open={fullViewOpen}
        title={selected?.module.title}
        footer={null}
        centered
        destroyOnHidden
        width="min(1000px, 100vw)"
        onCancel={() => setFullViewOpen(false)}
        styles={{ body: { maxHeight: 'calc(100vh - 8rem)', overflowY: 'auto' } }}
      >
        {selected?.content && (
          <div
            className={`text-[#08060d] ${TEXT_HTML_CLASS}`}
            dangerouslySetInnerHTML={{ __html: selected.content.content_text }}
          />
        )}
      </Modal>
    </>
  )
}
