import { ClockCircleOutlined, LinkOutlined, UploadOutlined } from '@ant-design/icons'
import { Alert, Button, Empty, Input, Skeleton, Tag } from 'antd'
import { useEffect, useMemo, useState } from 'react'

import { useAuth } from '@/auth/AuthContext'
import {
  createSubmission,
  listAssignments,
  listSubmissions,
  notifyEarnedBadges,
  notifyError,
  notifySuccess,
  updateSubmission,
} from '@/api'
import { useNow } from '@/hooks/useNow'
import type { Assignment } from '@/types/content'
import type { CourseModule } from '@/types/course'
import type { Submission } from '@/types/submission'

interface AssignmentSubmitPanelProps {
  module: CourseModule
  /** Dipanggil setelah submit sukses (parent memuat ulang progres). */
  onSubmitted: () => void
}

const validateUrl = (value: string): string | null => {
  const trimmed = value.trim()
  if (!trimmed) return 'Assignment link is required.'
  try {
    const parsed = new URL(trimmed)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return 'URL must start with http:// or https://'
    }
  } catch {
    return 'Enter a valid URL.'
  }
  return null
}

/**
 * Panel pengumpulan tugas untuk module berkategori `upload`.
 * Student menempelkan tautan hasil kerja (mis. Google Drive) — dibuat sebagai
 * Submission untuk dinilai mentor; module ikut otomatis ditandai selesai.
 * Tugas dibuat mentor (Assignment) — bila belum ada, panel menampilkan empty state.
 */
export function AssignmentSubmitPanel({ module, onSubmitted }: AssignmentSubmitPanelProps) {
  const { user } = useAuth()
  const userId = user?.id ?? null

  const [loading, setLoading] = useState(true)
  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [url, setUrl] = useState('')
  const [urlError, setUrlError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const dueAt = module.due_at
  const now = useNow()
  const isPastDue = dueAt != null && now > new Date(dueAt).getTime()
  const formattedDueAt = useMemo(() => {
    if (dueAt == null) return null
    return new Date(dueAt).toLocaleString('en-US', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }, [dueAt])

  // Muat assignment module + submission milik sendiri (remount per module via key).
  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const assignmentsPage = await listAssignments({
          course_module: module.id,
          page_size: 1,
        })
        const found = assignmentsPage.results[0] ?? null

        let existing: Submission | null = null
        if (found && userId != null) {
          const submissionsPage = await listSubmissions({
            assignment: found.id,
            user: userId,
            page_size: 1,
          })
          existing = submissionsPage.results[0] ?? null
        }

        if (cancelled) return
        setAssignment(found)
        setSubmission(existing)
        setUrl(existing?.submission_url ?? '')
      } catch (error) {
        if (!cancelled) notifyError(error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [module.id, userId])

  const handleSubmit = async () => {
    if (!assignment) return
    const validationError = validateUrl(url)
    setUrlError(validationError)
    if (validationError) return

    setSubmitting(true)
    try {
      const trimmed = url.trim()
      if (submission) {
        const saved = await updateSubmission(submission.id, {
          submission_url: trimmed,
        })
        setSubmission(saved)
      } else {
        const saved = await createSubmission({
          assignment: assignment.id,
          submission_url: trimmed,
        })
        setSubmission(saved)
        notifyEarnedBadges(saved.earned_badges)
      }
      setUrl(trimmed)

      notifySuccess('Assignment submitted successfully.')
      onSubmitted()
    } catch (error) {
      notifyError(error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Assignment</p>
      <h3 className="mt-0.5 text-lg font-semibold text-[#08060d]">
        {assignment?.name ?? module.title}
      </h3>
      {(assignment?.description || module.description) && (
        <p className="mt-1 whitespace-pre-line text-sm text-gray-600">
          {assignment?.description || module.description}
        </p>
      )}

      {formattedDueAt && (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-gray-600">
          <ClockCircleOutlined />
          <span>
            Deadline: <span className="font-medium">{formattedDueAt}</span>
          </span>
          {isPastDue && (
            <Tag color="red" className="mr-0">
              Past deadline
            </Tag>
          )}
        </p>
      )}
      {isPastDue && module.late_penalty_percent > 0 && (
        <Alert
          className="mt-3"
          type="warning"
          showIcon
          message={`Past deadline — points reduced by ${module.late_penalty_percent}%`}
          description="The assignment can still be submitted, but points going to the leaderboard will be reduced."
        />
      )}

      {loading ? (
        <Skeleton className="mt-4" active paragraph={{ rows: 3 }} />
      ) : !assignment ? (
        <Empty
          className="mt-4"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="There is no assignment from the mentor for this module yet."
        />
      ) : (
        <div className="mt-4 space-y-3">
          <label htmlFor="submission-url" className="block text-sm font-medium text-[#08060d]">
            Assignment link <span className="text-red-500">*</span>
          </label>
          <Input
            id="submission-url"
            value={url}
            onChange={(event) => {
              setUrl(event.target.value)
              if (urlError) setUrlError(null)
            }}
            placeholder="https://drive.google.com/..."
            status={urlError ? 'error' : undefined}
            allowClear
            size="large"
            onPressEnter={() => void handleSubmit()}
          />
          {urlError && <p className="text-sm text-red-500">{urlError}</p>}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="primary"
              size="large"
              loading={submitting}
              icon={<UploadOutlined />}
              onClick={() => void handleSubmit()}
            >
              {submission ? 'Update Link' : 'Submit Assignment'}
            </Button>
            {submission && (
              <a
                href={submission.submission_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-blue-600 no-underline hover:underline"
              >
                View submitted link <LinkOutlined />
              </a>
            )}
          </div>

          {submission && submission.submitted_on && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
              <span>
                Submitted{' '}
                {new Date(submission.submitted_on).toLocaleString('en-US', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
              {submission.is_late && (
                <Tag color="red" className="mr-0">
                  Late
                </Tag>
              )}
              {submission.is_graded ? (
                <Tag color="green" className="mr-0">
                  Score: {submission.score}
                  {submission.max_score != null && `/${submission.max_score}`}
                  {submission.is_late &&
                    submission.effective_score !== submission.score &&
                    ` · Effective: ${submission.effective_score}`}
                </Tag>
              ) : (
                <Tag color="orange" className="mr-0">
                  Pending mentor grading
                </Tag>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
