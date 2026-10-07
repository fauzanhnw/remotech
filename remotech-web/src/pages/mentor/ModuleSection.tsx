import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DeleteOutlined,
  EditOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'
import { Button, Collapse, Empty, Popconfirm, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import {
  deleteModule,
  deleteModuleContent,
  listModuleContents,
  listModules,
  notifyError,
  notifySuccess,
  updateModule,
  updateModuleContent,
} from '@/api'
import type { ModuleContent } from '@/types/content'
import type { CourseModule, ModuleCategory } from '@/types/course'
import { ContentFormModal } from './ContentFormModal'
import { ModuleFormModal } from './ModuleFormModal'

interface ModuleSectionProps {
  courseId: number
  /** false = tampilan baca-saja (bukan pemilik course). */
  canManage: boolean
}

const CATEGORY_ICONS: Record<ModuleCategory, ReactNode> = {
  text: <FileTextOutlined />,
  video: <PlayCircleOutlined />,
  upload: <UploadOutlined />,
  quiz: <QuestionCircleOutlined />,
}

/** Pengelolaan module + konten course: CRUD, reorder ↑↓, hapus (Popconfirm). */
export function ModuleSection({ courseId, canManage }: ModuleSectionProps) {
  const [modules, setModules] = useState<CourseModule[]>([])
  const [modulesLoading, setModulesLoading] = useState(true)
  const [modulesKey, setModulesKey] = useState(0)

  const [contents, setContents] = useState<Record<number, ModuleContent[]>>({})
  const [contentsStatus, setContentsStatus] = useState<Record<number, 'loading' | 'loaded'>>({})
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [moduleModal, setModuleModal] = useState<{
    open: boolean
    module: CourseModule | null
  }>({ open: false, module: null })
  const [contentModal, setContentModal] = useState<{
    open: boolean
    module: CourseModule | null
    content: ModuleContent | null
  }>({ open: false, module: null, content: null })

  const refreshModules = () => setModulesKey((value) => value + 1)

  // Reset loading saat query berubah (disesuaikan saat render, pola
  // "adjusting state when a prop changes" — lihat MentorCoursesPage).
  const [prevQuery, setPrevQuery] = useState({ courseId, modulesKey })
  if (prevQuery.courseId !== courseId || prevQuery.modulesKey !== modulesKey) {
    setPrevQuery({ courseId, modulesKey })
    setModulesLoading(true)
  }

  const loadContents = useCallback(
    async (moduleId: number, force = false) => {
      if (!force && contentsStatus[moduleId]) return
      setContentsStatus((prev) => ({ ...prev, [moduleId]: 'loading' }))
      try {
        const page = await listModuleContents({ module: moduleId, page_size: 100 })
        setContents((prev) => ({ ...prev, [moduleId]: page.results }))
        setContentsStatus((prev) => ({ ...prev, [moduleId]: 'loaded' }))
      } catch (error) {
        setContentsStatus((prev) => {
          const next = { ...prev }
          delete next[moduleId]
          return next
        })
        notifyError(error)
      }
    },
    [contentsStatus],
  )

  const refreshContents = (moduleId: number) => loadContents(moduleId, true)

  useEffect(() => {
    let cancelled = false

    listModules({ course: courseId, page_size: 100 })
      .then((page) => {
        if (!cancelled) setModules(page.results)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setModulesLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId, modulesKey])

  const markBusy = (key: string) => {
    setBusy((prev) => ({ ...prev, [key]: true }))
    return () =>
      setBusy((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
  }

  const handleReorderModule = async (module: CourseModule, direction: -1 | 1) => {
    const index = modules.findIndex((item) => item.id === module.id)
    const target = modules[index + direction]
    if (!target || module.sequence == null || target.sequence == null) return

    const done = markBusy(`module-${module.id}`)
    try {
      await updateModule(
        module.id,
        { sequence: target.sequence },
        { meta: { suppressErrorToast: true } },
      )
      await updateModule(
        target.id,
        { sequence: module.sequence },
        { meta: { suppressErrorToast: true } },
      )
      refreshModules()
    } catch (error) {
      notifyError(error)
    } finally {
      done()
    }
  }

  const handleDeleteModule = async (module: CourseModule) => {
    try {
      await deleteModule(module.id)
      notifySuccess('Module berhasil dihapus.')
      setContents((prev) => {
        const next = { ...prev }
        delete next[module.id]
        return next
      })
      setContentsStatus((prev) => {
        const next = { ...prev }
        delete next[module.id]
        return next
      })
      refreshModules()
    } catch (error) {
      notifyError(error)
    }
  }

  const handleReorderContent = async (
    moduleId: number,
    content: ModuleContent,
    direction: -1 | 1,
  ) => {
    const list = contents[moduleId] ?? []
    const index = list.findIndex((item) => item.id === content.id)
    const target = list[index + direction]
    if (!target || content.sequence == null || target.sequence == null) return

    const done = markBusy(`content-${content.id}`)
    try {
      await updateModuleContent(
        content.id,
        { sequence: target.sequence },
        { meta: { suppressErrorToast: true } },
      )
      await updateModuleContent(
        target.id,
        { sequence: content.sequence },
        { meta: { suppressErrorToast: true } },
      )
      await refreshContents(moduleId)
    } catch (error) {
      notifyError(error)
    } finally {
      done()
    }
  }

  const handleDeleteContent = async (moduleId: number, content: ModuleContent) => {
    try {
      await deleteModuleContent(content.id)
      notifySuccess('Konten berhasil dihapus.')
      await refreshContents(moduleId)
    } catch (error) {
      notifyError(error)
    }
  }

  const handlePanelChange = (keys: string[]) => {
    setActiveKeys(keys)
    keys.forEach((key) => void loadContents(Number(key)))
  }

  const renderContentList = (module: CourseModule) => {
    const status = contentsStatus[module.id]
    const list = contents[module.id] ?? []

    if (status === 'loading') return <Skeleton active paragraph={{ rows: 3 }} />

    if (!status || list.length === 0) {
      return <p className="text-sm text-gray-500">Belum ada konten untuk module ini.</p>
    }

    return (
      <ul className="space-y-2">
        {list.map((content, index) => {
          const isUrlContent = Boolean(content.content_url)

          return (
            <li
              key={content.id}
              className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3"
            >
              <div className="min-w-0 flex-1">
                {isUrlContent ? (
                  <a
                    href={content.content_url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate text-sm text-blue-600 no-underline hover:underline"
                  >
                    {content.content_url}
                  </a>
                ) : content.content_text.trim() ? (
                  // content_text sudah di-sanitize backend (whitelist nh3:
                  // tanpa script/iframe, URL http/https/mailto) sehingga aman dirender.
                  <div
                    className="max-h-64 overflow-y-auto text-sm leading-relaxed text-gray-800 [&_img]:my-2 [&_img]:max-h-80 [&_img]:w-auto [&_img]:rounded-md [&_img]:border [&_img]:border-gray-200 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1 [&_ul]:list-disc [&_ul]:pl-5"
                    dangerouslySetInnerHTML={{ __html: content.content_text }}
                  />
                ) : (
                  <p className="text-sm italic text-gray-400">Tidak ada isi</p>
                )}
                <p className="mt-1 text-xs text-gray-400">Sequence {index + 1}</p>
              </div>

              {canManage && (
                <div className="flex shrink-0 gap-1">
                  <Button
                    size="small"
                    type="text"
                    aria-label="Naikkan urutan"
                    disabled={index === 0}
                    loading={busy[`content-${content.id}`]}
                    icon={<ArrowUpOutlined />}
                    onClick={() => void handleReorderContent(module.id, content, -1)}
                  />
                  <Button
                    size="small"
                    type="text"
                    aria-label="Turunkan urutan"
                    disabled={index === list.length - 1}
                    loading={busy[`content-${content.id}`]}
                    icon={<ArrowDownOutlined />}
                    onClick={() => void handleReorderContent(module.id, content, 1)}
                  />
                  <Button
                    size="small"
                    type="text"
                    aria-label="Edit konten"
                    icon={<EditOutlined />}
                    onClick={() =>
                      setContentModal({ open: true, module, content })
                    }
                  />
                  <Popconfirm
                    title="Hapus konten ini?"
                    description="Konten dan media yang hanya dirujuknya ikut dihapus."
                    okText="Hapus"
                    okButtonProps={{ danger: true }}
                    cancelText="Batal"
                    onConfirm={() => void handleDeleteContent(module.id, content)}
                  >
                    <Button
                      size="small"
                      type="text"
                      danger
                      aria-label="Hapus konten"
                      icon={<DeleteOutlined />}
                    />
                  </Popconfirm>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <section className="mx-auto max-w-7xl px-4 pb-16 md:mx-8 xl:px-16">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold text-[#08060d]">Course Modules</h2>
        {canManage && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModuleModal({ open: true, module: null })}
          >
            Add Module
          </Button>
        )}
      </div>

      {modulesLoading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : modules.length === 0 ? (
        <Empty
          description={
            canManage
              ? 'Belum ada module. Klik Add Module untuk menambahkan.'
              : 'Belum ada module untuk course ini.'
          }
        />
      ) : (
        <Collapse
          activeKey={activeKeys}
          onChange={(keys) => handlePanelChange(keys as string[])}
          items={modules.map((module, index) => ({
            key: String(module.id),
            label: (
              <div className="flex items-center justify-between gap-3">
                <span className="flex min-w-0 items-center gap-2 font-medium">
                  {CATEGORY_ICONS[module.module_category]}
                  <span className="truncate">{module.title}</span>
                  <Tag className="mr-0">{module.point} poin</Tag>
                </span>

                {canManage && (
                  <span
                    className="flex gap-1"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <Button
                      size="small"
                      type="text"
                      aria-label="Naikkan urutan"
                      disabled={index === 0}
                      loading={busy[`module-${module.id}`]}
                      icon={<ArrowUpOutlined />}
                      onClick={() => void handleReorderModule(module, -1)}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="Turunkan urutan"
                      disabled={index === modules.length - 1}
                      loading={busy[`module-${module.id}`]}
                      icon={<ArrowDownOutlined />}
                      onClick={() => void handleReorderModule(module, 1)}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="Edit module"
                      icon={<EditOutlined />}
                      onClick={() => setModuleModal({ open: true, module })}
                    />
                    <Popconfirm
                      title="Hapus module ini?"
                      description="Semua konten dalam module ikut terhapus permanen."
                      okText="Hapus"
                      okButtonProps={{ danger: true }}
                      cancelText="Batal"
                      onConfirm={() => void handleDeleteModule(module)}
                    >
                      <Button
                        size="small"
                        type="text"
                        danger
                        aria-label="Hapus module"
                        icon={<DeleteOutlined />}
                      />
                    </Popconfirm>
                  </span>
                )}
              </div>
            ),
            children: (
              <div>
                {module.description && (
                  <p className="mb-3 text-sm leading-relaxed text-gray-600">
                    {module.description}
                  </p>
                )}

                {renderContentList(module)}

                {canManage && (
                  <Button
                    className="mt-3"
                    type="dashed"
                    icon={<PlusOutlined />}
                    onClick={() =>
                      setContentModal({ open: true, module, content: null })
                    }
                  >
                    Add Content
                  </Button>
                )}
              </div>
            ),
          }))}
        />
      )}

      <ModuleFormModal
        open={moduleModal.open}
        module={moduleModal.module}
        courseId={courseId}
        onClose={() => setModuleModal({ open: false, module: null })}
        onSaved={refreshModules}
      />

      <ContentFormModal
        open={contentModal.open}
        module={contentModal.module}
        content={contentModal.content}
        onClose={() => setContentModal({ open: false, module: null, content: null })}
        onSaved={() => {
          if (contentModal.module) refreshContents(contentModal.module.id)
        }}
      />
    </section>
  )
}
