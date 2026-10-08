import {
  CheckCircleFilled,
  CheckCircleOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { Button, Collapse, Empty, Progress, Skeleton, Tag } from 'antd'
import type { ReactNode } from 'react'
import { useCallback, useState } from 'react'

import { listModuleContents, notifyError } from '@/api'
import type { ModuleContent } from '@/types/content'
import type { CourseModule, ModuleCategory } from '@/types/course'

const CATEGORY_ICONS: Record<ModuleCategory, ReactNode> = {
  text: <FileTextOutlined />,
  video: <PlayCircleOutlined />,
  upload: <UploadOutlined />,
  quiz: <QuestionCircleOutlined />,
}

interface CurriculumListProps {
  modules: CourseModule[]
  /** Id module yang sudah ditandai selesai. */
  completedIds: Set<number>
  /** Id konten yang sudah dibuka (centang hijau di daftar konten). */
  viewedContentIds?: Set<number>
  /** Module yang sedang diproses tombol tandai-selesai (untuk spinner). */
  busyModuleId: number | null
  /** Id konten yang sedang ditampilkan di player. */
  selectedContentId: number | null
  /** Id module yang sedang ditampilkan di player (tanpa konten). */
  selectedModuleId?: number | null
  onToggleComplete: (module: CourseModule) => void
  onSelectContent: (module: CourseModule, content: ModuleContent) => void
  /** Pilih module tanpa konten (panel tugas module `upload`). */
  onSelectModule?: (module: CourseModule) => void
}

/**
 * List module & konten (kurikulum) dengan progres per module.
 * Konten per module dimuat lazy saat panel dibuka.
 */
export function CurriculumList({
  modules,
  completedIds,
  viewedContentIds,
  busyModuleId,
  selectedContentId,
  selectedModuleId,
  onToggleComplete,
  onSelectContent,
  onSelectModule,
}: CurriculumListProps) {
  const [contents, setContents] = useState<Record<number, ModuleContent[]>>({})
  const [contentsStatus, setContentsStatus] = useState<Record<number, 'loading' | 'loaded'>>(
    {},
  )
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  const loadContents = useCallback(
    async (moduleId: number) => {
      if (contentsStatus[moduleId]) return
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

  // Konten dimuat lazy: saat user membuka panel module.
  const handlePanelChange = (keys: string[]) => {
    setActiveKeys(keys)
    keys.forEach((key) => void loadContents(Number(key)))
  }

  const completedCount = modules.filter((module) => completedIds.has(module.id)).length
  const percent = modules.length ? Math.round((completedCount / modules.length) * 100) : 0

  const renderContentItems = (module: CourseModule) => {
    const status = contentsStatus[module.id]
    const list = contents[module.id] ?? []

    if (status === 'loading') return <Skeleton active paragraph={{ rows: 2 }} />

    if (!status || list.length === 0) {
      // Module upload: panel tugas (Kumpulkan tugas) sudah jelas tanpa daftar
      // konten — kosong berarti tidak ada lampiran, jangan tampilkan teks apa pun.
      if (module.module_category === 'upload') return null
      return <p className="text-sm text-gray-500">Belum ada konten untuk module ini.</p>
    }

    return (
      <ul className="list-none space-y-2 p-0">
        {list.map((content, index) => {
          const isSelected = selectedContentId === content.id

          return (
            <li key={content.id}>
              <button
                type="button"
                onClick={() => onSelectContent(module, content)}
                className={`flex w-full items-start gap-2 rounded-lg border p-2 text-left transition ${
                  isSelected
                    ? 'border-blue-300 bg-blue-50'
                    : 'border-gray-200 bg-white hover:border-blue-200 hover:bg-gray-50'
                }`}
              >
                <span className="mt-0.5 text-[#1677ff]">
                  {CATEGORY_ICONS[module.module_category]}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-[#08060d]">
                    Content {index + 1}
                  </span>
                </span>
                {viewedContentIds?.has(content.id) && (
                  <CheckCircleFilled
                    aria-label="Sudah dibuka"
                    className="mt-0.5 text-emerald-500"
                  />
                )}
              </button>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <div>
      <div className="border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-[#08060d]">Kurikulum</p>
          <p className="text-xs text-gray-500">{modules.length} module</p>
        </div>
        <Progress percent={percent} size="small" strokeWidth={6} className="mt-2 mb-0" />
        <p className="mt-1 text-xs text-gray-500">
          {completedCount}/{modules.length} module selesai
        </p>
      </div>

      <div className="p-3">
        {modules.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Belum ada module untuk course ini."
            className="py-8"
          />
        ) : (
          <Collapse
            size="small"
            activeKey={activeKeys}
            onChange={(keys) => handlePanelChange(keys as string[])}
            items={modules.map((module) => {
              const isDone = completedIds.has(module.id)
              // Progres upload/quiz diatur backend (submit tugas / quiz).
              const autoManaged =
                module.module_category === 'upload' ||
                module.module_category === 'quiz'

              return {
                key: String(module.id),
                label: (
                  <span className="flex min-w-0 items-center gap-2">
                    {!autoManaged && (
                      <span
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                      >
                        <Button
                          size="small"
                          type="text"
                          aria-label={isDone ? 'Batalkan tanda selesai' : 'Tandai selesai'}
                          loading={busyModuleId === module.id}
                          icon={
                            isDone ? (
                              <CheckCircleFilled className="text-emerald-500" />
                            ) : (
                              <CheckCircleOutlined />
                            )
                          }
                          onClick={() => onToggleComplete(module)}
                        />
                      </span>
                    )}
                    <span
                      className={
                        isDone && autoManaged
                          ? 'flex min-w-0 items-center gap-2 text-emerald-600'
                          : 'flex min-w-0 items-center gap-2'
                      }
                    >
                      {autoManaged && isDone && <CheckCircleFilled />}
                      <span className="text-[#1677ff]">
                        {CATEGORY_ICONS[module.module_category]}
                      </span>
                      <span className="truncate font-medium">{module.title}</span>
                    </span>
                    <Tag className="mr-0 shrink-0">{module.point} poin</Tag>
                  </span>
                ),
                children: (
                  <div>
                    {module.description && (
                      <p className="mb-3 text-sm leading-relaxed text-gray-600">
                        {module.description}
                      </p>
                    )}
                    {module.module_category === 'upload' && onSelectModule && (
                      <Button
                        block
                        className="mb-3"
                        type={selectedModuleId === module.id ? 'primary' : 'default'}
                        icon={<UploadOutlined />}
                        onClick={() => onSelectModule(module)}
                      >
                        Kumpulkan tugas
                      </Button>
                    )}
                    {module.module_category === 'quiz' && onSelectModule && (
                      <Button
                        block
                        className="mb-3"
                        type={selectedModuleId === module.id ? 'primary' : 'default'}
                        icon={<QuestionCircleOutlined />}
                        onClick={() => onSelectModule(module)}
                      >
                        {isDone ? 'Lihat Hasil Kuis' : 'Mulai Kuis'}
                      </Button>
                    )}
                    {module.module_category !== 'quiz' && renderContentItems(module)}
                  </div>
                ),
              }
            })}
          />
        )}
      </div>
    </div>
  )
}
