import { Alert, InputNumber, Modal, Skeleton } from 'antd'
import { useEffect, useState } from 'react'

import {
  gradeEssay,
  listQuestions,
  listUserAnswers,
  notifyError,
  notifySuccess,
  updateSubmission,
} from '@/api'
import type { Question, UserAnswer } from '@/types/quiz'
import type { Submission } from '@/types/submission'

interface GradingModalProps {
  /** Submission yang sedang dinilai; komponen dipasang hanya saat tidak null. */
  submission: Submission
  onClose: () => void
  onSaved: () => void
}

/**
 * Modal penilaian satu submission: tugas (upload) dinilai lewat skor
 * 0..poin module; quiz ber-essay dinilai per jawaban essay (bagian pilihan
 * otomatis). State sengaja di-reset lewat mount/unmount komponen.
 */
export function GradingModal({ submission, onClose, onSaved }: GradingModalProps) {
  const [uploadScore, setUploadScore] = useState<number | null>(
    submission.is_quiz ? null : submission.score || null,
  )
  const [quizQuestions, setQuizQuestions] = useState<Question[]>([])
  const [quizAnswers, setQuizAnswers] = useState<UserAnswer[]>([])
  const [essayScores, setEssayScores] = useState<Record<number, number>>({})
  const [quizLoading, setQuizLoading] = useState(
    submission.is_quiz && submission.module != null,
  )
  const [saving, setSaving] = useState(false)

  // Muat soal & jawaban quiz saat modal terbuka.
  useEffect(() => {
    if (!submission.is_quiz || submission.module == null) return
    let cancelled = false
    const module = submission.module
    const submissionId = submission.id

    Promise.all([
      listQuestions({ module, page_size: 100 }),
      listUserAnswers({ submission: submissionId, page_size: 100 }),
    ])
      .then(([questionPage, answerPage]) => {
        if (cancelled) return
        setQuizQuestions(questionPage.results)
        setQuizAnswers(answerPage.results)
        const initial: Record<number, number> = {}
        for (const answer of answerPage.results) {
          if (answer.is_correct === null) initial[answer.question] = answer.score ?? 0
        }
        setEssayScores(initial)
      })
      .catch((error) => {
        if (!cancelled) notifyError(error)
      })
      .finally(() => {
        if (!cancelled) setQuizLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [submission])

  const essayQuestions = quizQuestions.filter(
    (question) => question.question_type === 'essai',
  )
  const answerByQuestion = new Map(quizAnswers.map((answer) => [answer.question, answer]))
  const quizComplete =
    quizQuestions.length > 0 && quizAnswers.length >= quizQuestions.length
  const essayMissing = essayQuestions.some(
    (question) => !answerByQuestion.has(question.id),
  )

  const handleSave = async () => {
    setSaving(true)
    try {
      if (submission.is_quiz) {
        const answers = essayQuestions.map((question) => ({
          id: answerByQuestion.get(question.id)?.id ?? 0,
          score: essayScores[question.id] ?? 0,
        }))
        await gradeEssay(
          submission.id,
          { answers },
          { meta: { suppressErrorToast: true } },
        )
        notifySuccess('Penilaian essay tersimpan.')
      } else {
        await updateSubmission(
          submission.id,
          { score: uploadScore ?? 0 },
          { meta: { suppressErrorToast: true } },
        )
        notifySuccess('Skor tugas tersimpan.')
      }
      onSaved()
    } catch (error) {
      notifyError(error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      title={
        submission.is_quiz
          ? `Nilai Kuis — ${submission.module_title || 'Quiz'}`
          : `Nilai Tugas — ${submission.module_title || ''}`
      }
      okText="Simpan Penilaian"
      cancelText="Batal"
      confirmLoading={saving}
      okButtonProps={{
        disabled:
          submission.is_quiz &&
          (submission.module == null ||
            !quizComplete ||
            essayMissing ||
            essayQuestions.length === 0),
      }}
      onCancel={onClose}
      onOk={() => void handleSave()}
      destroyOnHidden
      width={720}
    >
      {!submission.is_quiz && (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Student</p>
            <p className="text-sm text-gray-600">{submission.user_name}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Tautan yang dikumpulkan</p>
            {submission.submission_url ? (
              <a
                href={submission.submission_url}
                target="_blank"
                rel="noreferrer"
                className="break-all text-sm text-blue-600 no-underline hover:underline"
              >
                {submission.submission_url}
              </a>
            ) : (
              <p className="text-sm text-gray-500">Belum ada tautan.</p>
            )}
          </div>
          <div>
            <p className="mb-1 text-sm font-medium text-gray-700">
              Skor (maksimal {submission.max_score ?? '-'})
            </p>
            <InputNumber
              min={0}
              max={submission.max_score ?? undefined}
              value={uploadScore}
              onChange={setUploadScore}
              placeholder="0"
              className="w-40"
            />
          </div>
        </div>
      )}

      {submission.is_quiz && (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Student</p>
            <p className="text-sm text-gray-600">{submission.user_name}</p>
          </div>

          {submission.module == null ? (
            <Alert
              type="warning"
              showIcon
              message="Belum ada jawaban masuk — student belum mengerjakan quiz ini."
            />
          ) : quizLoading ? (
            <Skeleton active paragraph={{ rows: 4 }} />
          ) : essayQuestions.length === 0 ? (
            <Alert
              type="info"
              showIcon
              message="Quiz ini dinilai otomatis dari jawaban pilihan — tidak ada soal essay."
            />
          ) : !quizComplete ? (
            <Alert
              type="warning"
              showIcon
              message="Quiz belum disubmit student — jawaban belum lengkap, belum bisa dinilai."
            />
          ) : (
            <>
              <p className="text-sm text-gray-500">
                Bagian pilihan dinilai otomatis ({submission.score} poin saat ini);
                nilai bagian essay di bawah — total maksimal{' '}
                {submission.max_score ?? '-'} poin.
              </p>
              <ul className="list-none space-y-4 p-0">
                {essayQuestions.map((question, index) => {
                  const answer = answerByQuestion.get(question.id)
                  return (
                    <li
                      key={question.id}
                      className="rounded-lg border border-gray-200 p-3"
                    >
                      <p className="text-sm font-medium text-[#08060d]">
                        {index + 1}. {question.question_text}
                      </p>
                      <p className="mt-2 whitespace-pre-line rounded bg-gray-50 p-2 text-sm text-gray-700">
                        {answer?.answer_text?.trim() || (
                          <span className="italic text-gray-400">
                            (jawaban kosong)
                          </span>
                        )}
                      </p>
                      <div className="mt-2 flex items-center gap-3">
                        <span className="text-sm text-gray-600">Skor essay:</span>
                        <InputNumber
                          min={0}
                          max={submission.max_score ?? undefined}
                          value={essayScores[question.id] ?? 0}
                          onChange={(value) =>
                            setEssayScores((prev) => ({
                              ...prev,
                              [question.id]: value ?? 0,
                            }))
                          }
                          className="w-28"
                        />
                      </div>
                    </li>
                  )
                })}
              </ul>
            </>
          )}
        </div>
      )}
    </Modal>
  )
}
