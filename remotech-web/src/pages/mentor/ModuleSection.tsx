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
  deleteAssignment,
  deleteModule,
  deleteModuleContent,
  deleteQuestion,
  listAssignments,
  listQuestions,
  listModuleContents,
  listModules,
  notifyError,
  notifySuccess,
  updateModule,
  updateModuleContent,
} from '@/api'
import type { Assignment, ModuleContent } from '@/types/content'
import type { CourseModule, ModuleCategory } from '@/types/course'
import type { Question } from '@/types/quiz'
import { AssignmentFormModal } from './AssignmentFormModal'
import { ContentFormModal } from './ContentFormModal'
import { ModuleFormModal } from './ModuleFormModal'
import { QuestionFormModal } from './QuestionFormModal'

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

const QUESTION_TYPE_LABELS: Record<string, string> = {
  choices: 'Multiple Choice',
  boolean: 'True/False',
  essai: 'Essay',
}

/**
 * Pengelolaan module + isinya: CRUD module, reorder ↑↓, hapus.
 * Isi per kategori: text/video → konten; upload → assignment (tugas);
 * quiz → daftar soal + opsi.
 */
export function ModuleSection({ courseId, canManage }: ModuleSectionProps) {
  const [modules, setModules] = useState<CourseModule[]>([])
  const [modulesLoading, setModulesLoading] = useState(true)
  const [modulesKey, setModulesKey] = useState(0)

  const [contents, setContents] = useState<Record<number, ModuleContent[]>>({})
  const [contentsStatus, setContentsStatus] = useState<Record<number, 'loading' | 'loaded'>>({})
  const [assignments, setAssignments] = useState<Record<number, Assignment | null>>({})
  const [assignmentStatus, setAssignmentStatus] = useState<
    Record<number, 'loading' | 'loaded'>
  >({})
  const [questions, setQuestions] = useState<Record<number, Question[]>>({})
  const [questionStatus, setQuestionStatus] = useState<Record<number, 'loading' | 'loaded'>>({})
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
  const [assignmentModal, setAssignmentModal] = useState<{
    open: boolean
    module: CourseModule | null
    assignment: Assignment | null
  }>({ open: false, module: null, assignment: null })
  const [questionModal, setQuestionModal] = useState<{
    open: boolean
    module: CourseModule | null
    question: Question | null
  }>({ open: false, module: null, question: null })

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

  const loadAssignment = useCallback(
    async (moduleId: number, force = false) => {
      if (!force && assignmentStatus[moduleId]) return
      setAssignmentStatus((prev) => ({ ...prev, [moduleId]: 'loading' }))
      try {
        const page = await listAssignments({ course_module: moduleId, page_size: 1 })
        setAssignments((prev) => ({ ...prev, [moduleId]: page.results[0] ?? null }))
        setAssignmentStatus((prev) => ({ ...prev, [moduleId]: 'loaded' }))
      } catch (error) {
        setAssignmentStatus((prev) => {
          const next = { ...prev }
          delete next[moduleId]
          return next
        })
        notifyError(error)
      }
    },
    [assignmentStatus],
  )

  const loadQuestions = useCallback(
    async (moduleId: number, force = false) => {
      if (!force && questionStatus[moduleId]) return
      setQuestionStatus((prev) => ({ ...prev, [moduleId]: 'loading' }))
      try {
        const page = await listQuestions({ module: moduleId, page_size: 100 })
        setQuestions((prev) => ({ ...prev, [moduleId]: page.results }))
        setQuestionStatus((prev) => ({ ...prev, [moduleId]: 'loaded' }))
      } catch (error) {
        setQuestionStatus((prev) => {
          const next = { ...prev }
          delete next[moduleId]
          return next
        })
        notifyError(error)
      }
    },
    [questionStatus],
  )

  const refreshContents = (moduleId: number) => loadContents(moduleId, true)
  const refreshAssignment = (moduleId: number) => loadAssignment(moduleId, true)
  const refreshQuestions = (moduleId: number) => loadQuestions(moduleId, true)

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
      notifySuccess('Module deleted.')
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
      setAssignments((prev) => {
        const next = { ...prev }
        delete next[module.id]
        return next
      })
      setQuestions((prev) => {
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
      notifySuccess('Content deleted.')
      await refreshContents(moduleId)
    } catch (error) {
      notifyError(error)
    }
  }

  const handleDeleteAssignment = async (module: CourseModule) => {
    const assignment = assignments[module.id]
    if (!assignment) return
    try {
      await deleteAssignment(assignment.id)
      notifySuccess('Assignment deleted.')
      await refreshAssignment(module.id)
    } catch (error) {
      notifyError(error)
    }
  }

  const handleDeleteQuestion = async (moduleId: number, question: Question) => {
    try {
      await deleteQuestion(question.id)
      notifySuccess('Question deleted.')
      await refreshQuestions(moduleId)
    } catch (error) {
      // Termasuk penolakan bila soal sudah pernah dijawab (toast interceptor).
      notifyError(error)
    }
  }

  const handlePanelChange = (keys: string[]) => {
    setActiveKeys(keys)
    keys.forEach((key) => {
      const moduleId = Number(key)
      const module = modules.find((item) => item.id === moduleId)
      if (!module) return
      if (module.module_category === 'upload') void loadAssignment(moduleId)
      else if (module.module_category === 'quiz') void loadQuestions(moduleId)
      else void loadContents(moduleId)
    })
  }

  const renderContentList = (module: CourseModule) => {
    const status = contentsStatus[module.id]
    const list = contents[module.id] ?? []

    if (status === 'loading') return <Skeleton active paragraph={{ rows: 3 }} />

    if (!status || list.length === 0) {
      return <p className="text-sm text-gray-500">No content in this module yet.</p>
    }

    return (
      <ul className="list-none space-y-2 p-0">
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
                  <p className="text-sm italic text-gray-400">No content</p>
                )}
                <p className="mt-1 text-xs text-gray-400">Sequence {index + 1}</p>
              </div>

              {canManage && (
                <div className="flex shrink-0 gap-1">
                  <Button
                    size="small"
                    type="text"
                    aria-label="Move up"
                    disabled={index === 0}
                    loading={busy[`content-${content.id}`]}
                    icon={<ArrowUpOutlined />}
                    onClick={() => void handleReorderContent(module.id, content, -1)}
                  />
                  <Button
                    size="small"
                    type="text"
                    aria-label="Move down"
                    disabled={index === list.length - 1}
                    loading={busy[`content-${content.id}`]}
                    icon={<ArrowDownOutlined />}
                    onClick={() => void handleReorderContent(module.id, content, 1)}
                  />
                  <Button
                    size="small"
                    type="text"
                    aria-label="Edit content"
                    icon={<EditOutlined />}
                    onClick={() =>
                      setContentModal({ open: true, module, content })
                    }
                  />
                  <Popconfirm
                    title="Delete this content?"
                    description="The content and any media it only references will be deleted as well."
                    okText="Delete"
                    okButtonProps={{ danger: true }}
                    cancelText="Cancel"
                    onConfirm={() => void handleDeleteContent(module.id, content)}
                  >
                    <Button
                      size="small"
                      type="text"
                      danger
                      aria-label="Delete content"
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

  const renderAssignment = (module: CourseModule) => {
    const status = assignmentStatus[module.id]
    const assignment = assignments[module.id] ?? null

    if (status === 'loading') return <Skeleton active paragraph={{ rows: 2 }} />

    if (!assignment) {
      return (
        <div className="rounded-lg border border-dashed border-gray-300 p-3">
          <p className="text-sm text-gray-500">
            No assignment yet. Students submit their work links through this
            assignment.
          </p>
          {canManage && (
            <Button
              className="mt-2"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAssignmentModal({ open: true, module, assignment: null })}
            >
              Create Assignment
            </Button>
          )}
        </div>
      )
    }

    return (
      <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[#08060d]">{assignment.name}</p>
          <p className="mt-1 whitespace-pre-line text-sm text-gray-600">
            {assignment.description || 'No description.'}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Where students submit their work links.
          </p>
        </div>
        {canManage && (
          <div className="flex shrink-0 gap-1">
            <Button
              size="small"
              type="text"
              aria-label="Edit assignment"
              icon={<EditOutlined />}
              onClick={() =>
                setAssignmentModal({ open: true, module, assignment })
              }
            />
            <Popconfirm
              title="Delete this assignment?"
              description="Student submissions on this assignment will be permanently deleted as well."
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
              onConfirm={() => void handleDeleteAssignment(module)}
            >
              <Button
                size="small"
                type="text"
                danger
                aria-label="Delete assignment"
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </div>
        )}
      </div>
    )
  }

  const renderQuestions = (module: CourseModule) => {
    const status = questionStatus[module.id]
    const list = questions[module.id] ?? []

    return (
      <div>
        {status === 'loading' ? (
          <Skeleton active paragraph={{ rows: 3 }} />
        ) : list.length === 0 ? (
          <p className="text-sm text-gray-500">No questions in this quiz yet.</p>
        ) : (
          <ul className="list-none space-y-2 p-0">
            {list.map((question, index) => (
              <li
                key={question.id}
                className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-gray-400">
                      {index + 1}.
                    </span>
                    <Tag className="mr-0">
                      {QUESTION_TYPE_LABELS[question.question_type] ??
                        question.question_type}
                    </Tag>
                    <span className="text-sm font-medium text-[#08060d]">
                      {question.question_text}
                    </span>
                  </div>
                  {question.question_type !== 'essai' && (
                    <ul className="mt-2 list-none space-y-1 p-0 pl-6">
                      {question.options.map((option, optionIndex) => (
                        <li key={option.id} className="text-xs text-gray-600">
                          {String.fromCharCode(65 + optionIndex)}. {option.option_text}
                          {option.is_correct && (
                            <span className="ml-1 font-semibold text-emerald-600">
                              (correct)
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                {canManage && (
                  <div className="flex shrink-0 gap-1">
                    <Button
                      size="small"
                      type="text"
                      aria-label="Edit question"
                      icon={<EditOutlined />}
                      onClick={() => setQuestionModal({ open: true, module, question })}
                    />
                    <Popconfirm
                      title="Delete this question?"
                      description="It cannot be deleted once students have attempted it."
                      okText="Delete"
                      okButtonProps={{ danger: true }}
                      cancelText="Cancel"
                      onConfirm={() => void handleDeleteQuestion(module.id, question)}
                    >
                      <Button
                        size="small"
                        type="text"
                        danger
                        aria-label="Delete question"
                        icon={<DeleteOutlined />}
                      />
                    </Popconfirm>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        {canManage && (
          <Button
            className="mt-3"
            type="dashed"
            icon={<PlusOutlined />}
            onClick={() => setQuestionModal({ open: true, module, question: null })}
          >
            Add Question
          </Button>
        )}
      </div>
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
              ? 'No modules yet. Click Add Module to add one.'
              : 'No modules in this course yet.'
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
                  <Tag className="mr-0">{module.point} points</Tag>
                </span>

                {canManage && (
                  <span
                    className="flex gap-1"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <Button
                      size="small"
                      type="text"
                      aria-label="Move up"
                      disabled={index === 0}
                      loading={busy[`module-${module.id}`]}
                      icon={<ArrowUpOutlined />}
                      onClick={() => void handleReorderModule(module, -1)}
                    />
                    <Button
                      size="small"
                      type="text"
                      aria-label="Move down"
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
                      title="Delete this module?"
                      description="All content in this module will be permanently deleted as well."
                      okText="Delete"
                      okButtonProps={{ danger: true }}
                      cancelText="Cancel"
                      onConfirm={() => void handleDeleteModule(module)}
                    >
                      <Button
                        size="small"
                        type="text"
                        danger
                        aria-label="Delete module"
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

                {module.module_category === 'upload' && renderAssignment(module)}
                {module.module_category === 'quiz' && renderQuestions(module)}
                {(module.module_category === 'text' ||
                  module.module_category === 'video') &&
                  renderContentList(module)}

                {canManage &&
                  (module.module_category === 'text' ||
                    module.module_category === 'video') && (
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

      <AssignmentFormModal
        open={assignmentModal.open}
        module={assignmentModal.module}
        assignment={assignmentModal.assignment}
        onClose={() =>
          setAssignmentModal({ open: false, module: null, assignment: null })
        }
        onSaved={() => {
          if (assignmentModal.module) refreshAssignment(assignmentModal.module.id)
        }}
      />

      <QuestionFormModal
        open={questionModal.open}
        module={questionModal.module?.id ?? 0}
        question={questionModal.question}
        onClose={() =>
          setQuestionModal({ open: false, module: null, question: null })
        }
        onSaved={() => {
          if (questionModal.module) refreshQuestions(questionModal.module.id)
        }}
      />
    </section>
  )
}
