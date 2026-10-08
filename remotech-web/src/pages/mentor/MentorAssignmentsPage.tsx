import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Empty, Input, Select, Skeleton, Space, Tag, Tooltip} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listSubmissions, notifyError } from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { Submission } from '@/types/submission'

/** Ringkasan penilaian satu module: total submission & yang belum dinilai. */
interface ModuleGradingCard {
  module: number
  moduleTitle: string
  courseTitle: string
  hasQuiz: boolean
  hasTask: boolean
  total: number
  pending: number
}

type TypeFilter = 'all' | 'quiz' | 'task'

function buildCards(submissions: Submission[]): ModuleGradingCard[] {
  const byModule = new Map<number, ModuleGradingCard>()

  for (const submission of submissions) {
    if (submission.module == null) continue
    const card = byModule.get(submission.module) ?? {
      module: submission.module,
      moduleTitle: submission.module_title || 'Module tanpa judul',
      courseTitle: submission.course_title || '—',
      hasQuiz: false,
      hasTask: false,
      total: 0,
      pending: 0,
    }
    if (submission.is_quiz) card.hasQuiz = true
    else card.hasTask = true
    card.total += 1
    if (!submission.is_graded) card.pending += 1
    byModule.set(submission.module, card)
  }

  return [...byModule.values()].sort(
    (a, b) =>
      b.pending - a.pending ||
      b.total - a.total ||
      a.moduleTitle.localeCompare(b.moduleTitle),
  )
}

/**
 * Penilaian: daftar module yang punya submission (tugas upload / quiz),
 * diurutkan dari yang paling banyak belum dinilai. Klik kartu untuk melihat
 * daftar submission pada module tersebut.
 */
export function MentorAssignmentsPage() {
  usePageTitle('Penilaian')

  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [search, setSearch] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    listSubmissions({ page_size: 100 })
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
  }, [reloadKey])

  const cards = useMemo(() => buildCards(submissions), [submissions])
  const visibleCards = useMemo(() => {
    const query = search.trim().toLowerCase()
    return cards.filter((card) => {
      if (typeFilter === 'quiz' && !card.hasQuiz) return false
      if (typeFilter === 'task' && !card.hasTask) return false
      if (
        query &&
        !card.moduleTitle.toLowerCase().includes(query) &&
        !card.courseTitle.toLowerCase().includes(query)
      ) {
        return false
      }
      return true
    })
  }, [cards, typeFilter, search])
  const pendingTotal = visibleCards.reduce((sum, card) => sum + card.pending, 0)

  return (
    <section className="mx-auto max-w px-4 pt-8 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-[#08060d]">Penilaian Penugasan</h2>
          <p className="text-sm text-gray-500">
            Module dengan submission tugas dan kuis
            {pendingTotal > 0 && (
              <span className="ml-1 font-medium text-orange-600">
                {pendingTotal} submission belum dinilai.
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap sm:flex-nowrap gap-3">
        <Input
          allowClear
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="Cari judul module atau course..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-full"
        />
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
          <Tooltip title="Refresh">
            <Button icon={<ReloadOutlined />} onClick={() => void load()}>
          </Button>
          </Tooltip>
        </Space>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} active paragraph={{ rows: 3 }} />
          ))}
        </div>
      ) : visibleCards.length === 0 ? (
        <Empty
          description={
            search.trim()
              ? 'Tidak ada module yang cocok dengan pencarian.'
              : typeFilter === 'all'
                ? 'Belum ada submission dari course-mu.'
                : `Tidak ada module ${
                    typeFilter === 'quiz' ? 'kuis' : 'tugas'
                  } untuk filter ini.`
          }
          className="py-16"
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4">
          {visibleCards.map((card) => (
            <Link
              key={card.module}
              to={`/mentor/assignments/${card.module}`}
              className="group flex flex-col rounded-xl border border-gray-200 bg-white p-4 no-underline shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <p className="truncate text-xs text-gray-500">{card.courseTitle}</p>
              <h3 className="mt-1 line-clamp-2 text-base font-semibold text-[#08060d]">
                {card.moduleTitle}
              </h3>

              <div className="mt-3 flex flex-wrap items-center gap-1">
                {card.hasQuiz && <Tag color="purple" className="mr-0">Kuis</Tag>}
                {card.hasTask && <Tag color="blue" className="mr-0">Tugas</Tag>}
              </div>

              <div className="mt-auto flex items-center justify-between pt-4">
                <span className="text-xs text-gray-500">
                  {card.total} submission
                </span>
                {card.pending > 0 ? (
                  <span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-600">
                    {card.pending} belum dinilai
                  </span>
                ) : (
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                    Semua sudah dinilai
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
