import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Empty, Input, Select, Skeleton, Space, Tag, Tooltip } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import {
  listAssignments,
  listEnrollments,
  listModules,
  listProgress,
  listQuestions,
  listSubmissions,
  notifyError,
} from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { CourseEnrollment } from '@/types/enrollment'
import type { CourseModule } from '@/types/course'
import type { Submission } from '@/types/submission'
import { fetchAllPages } from '@/utils/paginate'

type Kind = 'task' | 'quiz'
type Status = 'todo' | 'doing' | 'pending' | 'graded'
type TypeFilter = 'all' | Kind
type StatusFilter = 'all' | Status

/** Satu baris penugasan student: module upload/quiz pada course yang di-enroll. */
interface AssignmentItem {
  module: number
  moduleTitle: string
  course: number
  courseTitle: string
  sequence: number | null
  kind: Kind
  status: Status
  score: number | null
  maxScore: number | null
}

const STATUS_META: Record<Status, { label: string; className: string }> = {
  todo: { label: 'Belum dikerjakan', className: 'bg-gray-100 text-gray-600' },
  doing: { label: 'Sedang dikerjakan', className: 'bg-blue-50 text-blue-600' },
  pending: { label: 'Menunggu penilaian', className: 'bg-orange-50 text-orange-600' },
  graded: { label: 'Sudah dinilai', className: 'bg-emerald-50 text-emerald-600' },
}

const ACTION_LABEL: Record<Status, string> = {
  todo: 'Kerjakan',
  doing: 'Lanjutkan',
  pending: 'Lihat detail',
  graded: 'Lihat hasil',
}

const STATUS_RANK: Record<Status, number> = { todo: 0, doing: 1, pending: 2, graded: 3 }

/**
 * Susun daftar penugasan dari data sweep:
 * - module `upload` hanya diikut bila mentor sudah membuat Assignment;
 * - module `quiz` hanya diikut bila soalnya sudah ada;
 * - status diturunkan dari submission milik sendiri + penandaan selesai
 *   (quiz yang masih draft punya submission tapi module belum `finish`).
 */
function buildItems(
  enrollments: CourseEnrollment[],
  modules: CourseModule[],
  assignmentModuleIds: Set<number>,
  questionModuleIds: Set<number>,
  submissions: Submission[],
  finishedModuleIds: Set<number>,
): AssignmentItem[] {
  const courseTitleByCourse = new Map(
    enrollments.map((enrollment) => [enrollment.course.id, enrollment.course.title]),
  )
  const submissionByModule = new Map<number, Submission>()
  for (const submission of submissions) {
    if (submission.module != null) submissionByModule.set(submission.module, submission)
  }

  const items: AssignmentItem[] = []

  for (const module of modules) {
    const courseTitle = courseTitleByCourse.get(module.course)
    if (courseTitle === undefined) continue

    const kind: Kind = module.module_category === 'quiz' ? 'quiz' : 'task'
    if (kind === 'task' && !assignmentModuleIds.has(module.id)) continue
    if (kind === 'quiz' && !questionModuleIds.has(module.id)) continue

    const submission = submissionByModule.get(module.id) ?? null
    const finished = finishedModuleIds.has(module.id)
    const status: Status = !submission
      ? 'todo'
      : submission.is_graded
        ? 'graded'
        : finished
          ? 'pending'
          : 'doing'

    items.push({
      module: module.id,
      moduleTitle: module.title,
      course: module.course,
      courseTitle,
      sequence: module.sequence,
      kind,
      status,
      score: submission?.score ?? null,
      maxScore: submission?.max_score ?? null,
    })
  }

  return items.sort(
    (a, b) =>
      STATUS_RANK[a.status] - STATUS_RANK[b.status] ||
      a.courseTitle.localeCompare(b.courseTitle) ||
      (a.sequence ?? Number.MAX_SAFE_INTEGER) - (b.sequence ?? Number.MAX_SAFE_INTEGER) ||
      a.moduleTitle.localeCompare(b.moduleTitle),
  )
}

/**
 * My Assignment: seluruh tugas (upload) & kuis dari course yang di-enroll,
 * lengkap dengan status pengerjaan/penilaian. Kartu mengarahkan student
 * langsung ke panel pengerjaan di halaman course (`?module=<id>`).
 */
export function MyAssignmentsPage() {
  usePageTitle('My Assignment')

  const { user, profileLoaded } = useAuth()
  const userId = user?.id ?? null

  const [items, setItems] = useState<AssignmentItem[]>([])
  const [enrollmentCount, setEnrollmentCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const load = useCallback(() => {
    setLoading(true)
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    // Tunggu profil login agar filter `user` pada submission tidak kosong.
    if (!profileLoaded) return
    let cancelled = false

    void (async () => {
      try {
        const [
          enrollments,
          modules,
          assignments,
          questions,
          submissions,
          progress,
        ] = await Promise.all([
          fetchAllPages((params) => listEnrollments(params)),
          fetchAllPages((params) => listModules(params)),
          fetchAllPages((params) => listAssignments(params)),
          fetchAllPages((params) => listQuestions(params)),
          fetchAllPages((params) =>
            listSubmissions(userId == null ? params : { ...params, user: userId }),
          ),
          fetchAllPages((params) => listProgress(params)),
        ])

        if (cancelled) return
        setEnrollmentCount(enrollments.length)
        setItems(
          buildItems(
            enrollments,
            modules,
            new Set(assignments.map((assignment) => assignment.course_module)),
            new Set(questions.map((question) => question.module)),
            submissions,
            new Set(
              progress
                .filter((row) => row.status === 'finish')
                .map((row) => row.module),
            ),
          ),
        )
      } catch (error) {
        if (!cancelled) notifyError(error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [reloadKey, userId, profileLoaded])

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    return items.filter((item) => {
      if (typeFilter !== 'all' && item.kind !== typeFilter) return false
      if (statusFilter !== 'all' && item.status !== statusFilter) return false
      if (
        query &&
        !item.moduleTitle.toLowerCase().includes(query) &&
        !item.courseTitle.toLowerCase().includes(query)
      ) {
        return false
      }
      return true
    })
  }, [items, search, typeFilter, statusFilter])

  const summary = useMemo(() => {
    const counts: Record<Status, number> = { todo: 0, doing: 0, pending: 0, graded: 0 }
    for (const item of visible) counts[item.status] += 1
    const parts: string[] = []
    if (counts.todo > 0) parts.push(`${counts.todo} belum dikerjakan`)
    if (counts.doing > 0) parts.push(`${counts.doing} sedang dikerjakan`)
    if (counts.pending > 0) parts.push(`${counts.pending} menunggu penilaian`)
    return parts.join(' · ')
  }, [visible])

  const emptyDescription = () => {
    if (enrollmentCount === 0) return 'Kamu belum enroll course mana pun.'
    if (items.length === 0)
      return 'Belum ada tugas atau kuis pada course yang kamu ikuti.'
    if (search.trim()) return 'Tidak ada assignment yang cocok dengan pencarian.'
    return 'Tidak ada assignment untuk filter ini.'
  }

  return (
    <section className="mx-auto max-w px-4 py-10 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#08060d]">My Assignment</h1>
          <p className="mt-2 text-gray-600">
            Tugas dan kuis dari course yang kamu ambil
            {summary && (
              <span className="ml-1 font-medium text-orange-600">{summary}</span>
            )}
          </p>
        </div>
        <Space>
          <Select
            value={typeFilter}
            onChange={setTypeFilter}
            options={[
              { value: 'all', label: 'Semua tipe' },
              { value: 'task', label: 'Tugas' },
              { value: 'quiz', label: 'Kuis' },
            ]}
            style={{ width: 140 }}
          />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'all', label: 'Semua status' },
              { value: 'todo', label: 'Belum dikerjakan' },
              { value: 'doing', label: 'Sedang dikerjakan' },
              { value: 'pending', label: 'Menunggu penilaian' },
              { value: 'graded', label: 'Sudah dinilai' },
            ]}
            style={{ width: 170 }}
          />
          <Tooltip title="Refresh">
            <Button icon={<ReloadOutlined />} onClick={() => void load()}>
          </Button>
          </Tooltip>
        </Space>
      </div>

      <div className="mb-4">
        <Input
          allowClear
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="Cari judul module atau course..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-sm"
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} active paragraph={{ rows: 3 }} />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <Empty description={emptyDescription()} className="py-16">
          {enrollmentCount === 0 && (
            <Link to="/courses" className="inline-flex">
              <Button type="primary">Jelajahi Katalog</Button>
            </Link>
          )}
        </Empty>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {visible.map((item) => (
            <Link
              key={item.module}
              to={`/my-courses/${item.course}?module=${item.module}`}
              className="group flex flex-col rounded-xl border border-gray-200 bg-white p-4 no-underline shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <p className="truncate text-xs text-gray-500">{item.courseTitle}</p>
              <h3 className="mt-1 line-clamp-2 text-base font-semibold text-[#08060d]">
                {item.moduleTitle}
              </h3>

              <div className="mt-3 flex flex-wrap items-center gap-1">
                <Tag color={item.kind === 'quiz' ? 'purple' : 'blue'} className="mr-0">
                  {item.kind === 'quiz' ? 'Kuis' : 'Tugas'}
                </Tag>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_META[item.status].className}`}
                >
                  {STATUS_META[item.status].label}
                </span>
              </div>

              <div className="mt-auto flex items-center justify-between pt-4">
                <span className="text-xs font-medium text-blue-600 group-hover:underline">
                  {ACTION_LABEL[item.status]} →
                </span>
                {item.status === 'graded' && (
                  <span className="text-xs font-semibold text-emerald-600">
                    Skor: {item.score}
                    {item.maxScore != null && `/${item.maxScore}`}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
