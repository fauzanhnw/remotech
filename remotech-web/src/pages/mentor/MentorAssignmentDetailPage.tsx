import { ArrowLeftOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Empty, Input, Select, Skeleton, Space, Table, Tag, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getCourse, getModule, listSubmissions, notifyError } from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import { NotFoundPage } from '@/pages/NotFoundPage'
import type { CourseModule } from '@/types/course'
import type { Submission } from '@/types/submission'
import { GradingModal } from './GradingModal'

type StatusFilter = 'all' | 'pending' | 'graded'
type TypeFilter = 'all' | 'quiz' | 'task'

function statusTag(submission: Submission): ReactNode {
  if (submission.is_quiz) {
    if (submission.reviewed_by === 'system') {
      return <Tag color="blue">Dinilai otomatis</Tag>
    }
    if (submission.reviewed_by) {
      return <Tag color="green">Dinilai mentor</Tag>
    }
    return <Tag color="orange">Menunggu penilaian essay</Tag>
  }
  if (submission.is_graded) return <Tag color="green">Dinilai</Tag>
  return <Tag color="orange">Belum dinilai</Tag>
}

/** Detail penilaian: daftar submission (tugas/kuis) dari satu module. */
export function MentorAssignmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const moduleId = Number(id)

  const invalidId = !Number.isInteger(moduleId) || moduleId <= 0

  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [search, setSearch] = useState('')

  // Judul module/course diambil dari submission; fallback ke API bila kosong.
  const [moduleInfo, setModuleInfo] = useState<CourseModule | null>(null)
  const [courseTitle, setCourseTitle] = useState('')

  const [grading, setGrading] = useState<Submission | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    if (invalidId) return
    let cancelled = false

    listSubmissions({ module: moduleId, page_size: 100 })
      .then((page) => {
        if (!cancelled) setSubmissions(page.results)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [moduleId, invalidId, reloadKey])

  useEffect(() => {
    if (invalidId || loading || submissions.length > 0 || moduleInfo) return
    let cancelled = false

    getModule(moduleId)
      .then((module) => {
        if (cancelled) return null
        setModuleInfo(module)
        return getCourse(module.course)
      })
      .then((course) => {
        if (!cancelled && course) setCourseTitle(course.title)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })

    return () => {
      cancelled = true
    }
  }, [invalidId, loading, submissions.length, moduleInfo, moduleId])

  const moduleTitle = useMemo(() => {
    const titled = submissions.find((submission) => submission.module_title)
    return titled?.module_title || moduleInfo?.title || `Module ${moduleId}`
  }, [submissions, moduleInfo, moduleId])

  const course = useMemo(() => {
    const titled = submissions.find((submission) => submission.course_title)
    return titled?.course_title || courseTitle
  }, [submissions, courseTitle])

  usePageTitle(moduleTitle)

  // Filter tipe hanya relevan bila module punya submission tugas & kuis.
  const hasMixedTypes =
    submissions.some((submission) => submission.is_quiz) &&
    submissions.some((submission) => !submission.is_quiz)

  const filtered = submissions.filter((submission) => {
    if (hasMixedTypes) {
      if (typeFilter === 'quiz' && !submission.is_quiz) return false
      if (typeFilter === 'task' && submission.is_quiz) return false
    }
    if (statusFilter === 'graded' && !submission.is_graded) return false
    if (statusFilter === 'pending' && submission.is_graded) return false
    const query = search.trim().toLowerCase()
    if (
      query &&
      !submission.user_name.toLowerCase().includes(query) &&
      !submission.submission_url.toLowerCase().includes(query)
    ) {
      return false
    }
    return true
  })

  const pendingCount = submissions.filter(
    (submission) => !submission.is_graded,
  ).length


  const columns: ColumnsType<Submission> = [
    {
      title: 'Student',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string) => <span className="font-medium">{name}</span>,
    },
    {
      title: 'Tipe',
      key: 'type',
      render: (_, submission) =>
        submission.is_quiz ? <Tag color="purple">Kuis</Tag> : <Tag color="blue">Tugas</Tag>,
    },
    {
      title: 'Tautan',
      key: 'link',
      render: (_, submission) =>
        submission.is_quiz ? (
          '—'
        ) : submission.submission_url ? (
          <a
            href={submission.submission_url}
            target="_blank"
            rel="noreferrer"
            className="break-all text-blue-600 no-underline hover:underline"
          >
            {submission.submission_url}
          </a>
        ) : (
          '—'
        ),
    },
    {
      title: 'Skor',
      key: 'score',
      render: (_, submission) => (
        <span>
          {submission.score}
          {submission.max_score != null && ` / ${submission.max_score}`}
        </span>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, submission) => statusTag(submission),
    },
    {
      title: '',
      key: 'actions',
      render: (_, submission) => (
        <Button
          size="small"
          type={submission.is_graded ? 'default' : 'primary'}
          onClick={() => setGrading(submission)}
        >
          {submission.is_graded ? 'Ubah Nilai' : 'Nilai'}
        </Button>
      ),
    },
  ]

  if (invalidId) return <NotFoundPage />

  return (
    <section className="mx-auto max-w-7xl px-4 pt-8 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6">
        <Link
          to="/mentor/assignments"
          className="inline-flex items-center gap-1 text-sm text-blue-600 no-underline hover:underline"
        >
          <ArrowLeftOutlined /> Kembali ke Penilaian
        </Link>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold text-[#08060d]">{moduleTitle}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {course}
              {pendingCount > 0 && (
                <span className="ml-1 font-medium text-orange-600">
                  — {pendingCount} submission belum dinilai.
                </span>
              )}
            </p>
          </div>
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined className="text-gray-400" />}
              placeholder="Cari student atau tautan..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ width: 220 }}
            />
            {hasMixedTypes && (
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
            )}
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'all', label: 'Semua status' },
                { value: 'pending', label: 'Belum dinilai' },
                { value: 'graded', label: 'Sudah dinilai' },
              ]}
              style={{ width: 160 }}
            />
            <Tooltip title="Refresh">
              <Button icon={<ReloadOutlined />} onClick={() => void load()}>
            </Button>
            </Tooltip>
          </Space>
        </div>
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : filtered.length === 0 ? (
        <Empty
          description={
            submissions.length === 0
              ? 'Belum ada submission pada module ini.'
              : search.trim()
                ? 'Tidak ada submission yang cocok dengan pencarian.'
                : 'Tidak ada submission untuk filter ini.'
          }
          className="py-16"
        />
      ) : (
        <Table<Submission>
          rowKey="id"
          columns={columns}
          dataSource={filtered}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          scroll={{ x: 900 }}
        />
      )}

      {grading && (
        <GradingModal
          submission={grading}
          onClose={() => setGrading(null)}
          onSaved={() => {
            setGrading(null)
            load()
          }}
        />
      )}
    </section>
  )
}
