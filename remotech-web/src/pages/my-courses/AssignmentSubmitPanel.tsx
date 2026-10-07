import { LinkOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Input, Skeleton } from 'antd'
import { useEffect, useState } from 'react'

import { useAuth } from '@/auth/AuthContext'
import {
  createAssignment,
  createSubmission,
  listAssignments,
  listSubmissions,
  markModuleComplete,
  notifyError,
  notifySuccess,
  updateSubmission,
} from '@/api'
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
  if (!trimmed) return 'Wajib isi tautan tugas.'
  try {
    const parsed = new URL(trimmed)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return 'URL harus diawali http:// atau https://'
    }
  } catch {
    return 'Masukkan URL yang valid.'
  }
  return null
}

/**
 * Panel pengumpulan tugas untuk module berkategori `upload`.
 * Student menempelkan tautan hasil kerja (mis. Google Drive) — dibuat sebagai
 * Submission untuk dinilai mentor; module ikut otomatis ditandai selesai.
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
    const validationError = validateUrl(url)
    setUrlError(validationError)
    if (validationError) return

    setSubmitting(true)
    try {
      let target = assignment
      if (!target) {
        // Belum ada assignment untuk module — buat saat pengumpulan pertama.
        target = await createAssignment({
          course_module: module.id,
          name: module.title,
          description: module.description || 'Kumpulkan tautan hasil pekerjaanmu di sini.',
        })
        setAssignment(target)
      }

      const trimmed = url.trim()
      const saved = submission
        ? await updateSubmission(submission.id, { submission_url: trimmed })
        : await createSubmission({ assignment: target.id, submission_url: trimmed })
      setSubmission(saved)
      setUrl(trimmed)

      // Jalur PATCH tidak otomatis menandai selesai di backend — jaga-jaga.
      await markModuleComplete(module.id, {
        meta: { suppressErrorToast: true },
      }).catch(() => undefined)

      notifySuccess('Tugas berhasil dikumpulkan.')
      onSubmitted()
    } catch (error) {
      notifyError(error)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Penugasan</p>
      <h3 className="mt-0.5 text-lg font-semibold text-[#08060d]">
        {assignment?.name ?? module.title}
      </h3>
      {(assignment?.description || module.description) && (
        <p className="mt-1 whitespace-pre-line text-sm text-gray-600">
          {assignment?.description || module.description}
        </p>
      )}

      {loading ? (
        <Skeleton className="mt-4" active paragraph={{ rows: 3 }} />
      ) : (
        <div className="mt-4 space-y-3">
          <label htmlFor="submission-url" className="block text-sm font-medium text-[#08060d]">
            Tautan tugas <span className="text-red-500">*</span>
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
              {submission ? 'Perbarui Tautan' : 'Kumpulkan Tugas'}
            </Button>
            {submission && (
              <a
                href={submission.submission_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-blue-600 no-underline hover:underline"
              >
                Lihat tautan yang dikirim <LinkOutlined />
              </a>
            )}
          </div>

          {submission && (
            <p className="text-xs text-gray-500">
              Terkumpul{' '}
              {new Date(submission.submit_on).toLocaleString('id-ID', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
              {submission.score > 0 && ` · Skor: ${submission.score}`}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
