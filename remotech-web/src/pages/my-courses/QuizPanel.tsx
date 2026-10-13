import { CheckCircleFilled, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { App as AntApp, Alert, Button, Input, Radio, Skeleton, Tag } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  notifyEarnedBadges,
  notifyError,
  notifySuccess,
  startQuiz,
  submitQuiz,
  upsertAnswer,
} from '@/api'
import { useNow } from '@/hooks/useNow'
import type { CourseModule } from '@/types/course'
import type { QuizResult, QuizSession, Question, UserAnswer } from '@/types/quiz'

interface QuizPanelProps {
  module: CourseModule
  /** Dipanggil setelah submit sukses (parent memuat ulang progres). */
  onSubmitted: () => void
}

interface AnswerMap {
  [questionId: number]: { question_option?: number; answer_text?: string }
}

/**
 * Panel pengerjaan quiz (module berkategori `quiz`).
 *
 * Alur: start (draft stabil antar buka) → jawaban tersimpan per soal
 * (upsert) → submit sekali jalan dengan konfirmasi dua mode:
 * belum lengkap = peringatan tanpa submit; lengkap = konfirmasi async.
 * Setelah final, menampilkan skor + review kunci jawaban.
 */
export function QuizPanel({ module, onSubmitted }: QuizPanelProps) {
  // Static Modal.confirm/warning tidak dirender di React 19 — pakai
  // instance dari antd <App> (lihat pola notification di App.tsx).
  const { modal } = AntApp.useApp()
  const [loading, setLoading] = useState(true)
  const [loadFailed, setLoadFailed] = useState(false)
  const [session, setSession] = useState<QuizSession | null>(null)
  const [answers, setAnswers] = useState<AnswerMap>({})
  const [savingIds, setSavingIds] = useState<Set<number>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<QuizResult | null>(null)

  const applySession = useCallback((data: QuizSession) => {
    setSession(data)
    setResult(data.result ?? null)
    const map: AnswerMap = {}
    for (const answer of data.answers) {
      map[answer.question] = {
        ...(answer.question_option != null
          ? { question_option: answer.question_option }
          : {}),
        ...(answer.answer_text ? { answer_text: answer.answer_text } : {}),
      }
    }
    setAnswers(map)
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const data = await startQuiz(module.id)
        if (!cancelled) applySession(data)
      } catch (error) {
        if (!cancelled) {
          setLoadFailed(true)
          notifyError(error)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [module.id, applySession])

  const questions = useMemo(() => session?.questions ?? [], [session])
  const completed = session?.completed ?? false

  const dueAt = module.due_at
  const now = useNow()
  const isPastDue = dueAt != null && now > new Date(dueAt).getTime()
  const formattedDueAt = useMemo(() => {
    if (dueAt == null) return null
    return new Date(dueAt).toLocaleString('id-ID', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }, [dueAt])

  const answeredCount = useMemo(
    () =>
      questions.filter((question) => {
        const answer = answers[question.id]
        if (question.question_type === 'essai') {
          return Boolean(answer?.answer_text?.trim())
        }
        return answer?.question_option != null
      }).length,
    [questions, answers],
  )

  const saveAnswer = async (
    question: Question,
    payload: { question_option?: number; answer_text?: string },
  ) => {
    if (!session) return
    setSavingIds((prev) => new Set(prev).add(question.id))
    try {
      await upsertAnswer(
        {
          submission: session.submission.id,
          question: question.id,
          ...payload,
        },
        { meta: { suppressErrorToast: true } },
      )
      setAnswers((prev) => ({ ...prev, [question.id]: payload }))
    } catch (error) {
      notifyError(error)
    } finally {
      setSavingIds((prev) => {
        const next = new Set(prev)
        next.delete(question.id)
        return next
      })
    }
  }

  const handlePickOption = (question: Question, optionId: number) => {
    void saveAnswer(question, { question_option: optionId })
  }

  const handleEssayChange = (question: Question, text: string) => {
    setAnswers((prev) => ({ ...prev, [question.id]: { answer_text: text } }))
  }

  const handleEssayBlur = (question: Question) => {
    const text = answers[question.id]?.answer_text ?? ''
    if (!text.trim()) return
    void saveAnswer(question, { answer_text: text })
  }

  const handleSubmit = () => {
    if (!session) return
    const missing = questions.length - answeredCount

    if (missing > 0) {
      modal.warning({
        title: 'Lengkapi semua jawaban',
        content: `Masih ada ${missing} soal yang belum dijawab. Semua soal wajib dijawab sebelum mengumpulkan.`,
      })
      return
    }

    const lateWarning =
      isPastDue && module.late_penalty_percent > 0
        ? ` Pengumpulan melewati tenggat — poin berkurang ${module.late_penalty_percent}%.`
        : ''

    modal.confirm({
      title: 'Kumpulkan jawaban?',
      content: module.allow_retake
        ? `Quiz ini bisa diulang. Skor terbaru yang akan dihitung. Jawaban pilihan dinilai otomatis; bagian essay dinilai mentor.${lateWarning}`
        : `Quiz hanya bisa disubmit satu kali. Setelah dikumpulkan, jawaban tidak bisa diubah. Jawaban pilihan dinilai otomatis; bagian essay dinilai mentor.${lateWarning}`,
      okText: 'Kumpulkan',
      cancelText: 'Periksa Lagi',
      onOk: async () => {
        setSubmitting(true)
        try {
          const data = await submitQuiz(module.id, session.submission.id)
          setSession(data)
          setResult(data.result ?? null)
          notifySuccess('Jawaban quiz berhasil dikumpulkan.')
          notifyEarnedBadges(data.earned_badges)
          onSubmitted()
        } catch (error) {
          notifyError(error)
        } finally {
          setSubmitting(false)
        }
      },
    })
  }

  const handleRetake = () => {
    modal.confirm({
      title: 'Mulai percobaan baru?',
      content:
        'Nilai attempt sebelumnya tetap tersimpan sebagai riwayat; skor attempt terbaru yang dihitung.',
      okText: 'Coba Lagi',
      cancelText: 'Batal',
      onOk: async () => {
        setSubmitting(true)
        try {
          // Backend membuat draft baru (allow_retake) saat attempt sudah final.
          const data = await startQuiz(module.id)
          applySession(data)
          notifySuccess('Percobaan baru dimulai. Semoga berhasil!')
        } catch (error) {
          notifyError(error)
        } finally {
          setSubmitting(false)
        }
      },
    })
  }

  if (loading) {
    return <Skeleton className="mt-4" active paragraph={{ rows: 6 }} />
  }

  if (loadFailed || !session) {
    return (
      <Alert
        type="error"
        showIcon
        message="Quiz tidak bisa dimuat"
        description="Pastikan kamu terdaftar pada course ini dan quiz sudah memiliki soal."
      />
    )
  }

  if (completed && result) {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Kuis</p>
        <h3 className="mt-0.5 text-lg font-semibold text-[#08060d]">{module.title}</h3>

        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div>
            <p className="text-xs text-gray-500">Skor</p>
            <p className="text-2xl font-bold text-[#08060d]">
              {result.score}
              <span className="text-base font-medium text-gray-500">
                /{result.max_score}
              </span>
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Jawaban benar</p>
            <p className="text-lg font-semibold text-[#08060d]">
              {result.correct}/{result.auto_total}
            </p>
          </div>
          {session.submission.is_late && (
            <Tag color="red" className="mr-0">
              Telat
            </Tag>
          )}
          {result.pending ? (
            <Tag color="orange" className="mr-0">
              Menunggu penilaian essay
            </Tag>
          ) : result.essay_count > 0 ? (
            <Tag color="green" className="mr-0">
              Selesai dinilai mentor
            </Tag>
          ) : (
            <Tag color="blue" className="mr-0">
              Dinilai otomatis
            </Tag>
          )}
          {module.allow_retake && (
            <Tag color="cyan" className="mr-0">
              Bisa diulang
            </Tag>
          )}
        </div>

        {result.pending && (
          <Alert
            className="mt-3"
            type="info"
            showIcon
            message="Skor sementara dari bagian pilihan. Skor final menyusul setelah mentor menilai essay."
          />
        )}

        {module.allow_retake && (
          <div className="mt-3">
            <Button
              type="primary"
              loading={submitting}
              onClick={handleRetake}
            >
              Coba Lagi
            </Button>
          </div>
        )}

        <div className="mt-4 space-y-4">
          {questions.map((question, index) => (
            <QuestionReview
              key={question.id}
              index={index}
              question={question}
              answer={session.answers.find((item) => item.question === question.id)}
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Kuis</p>
      <div className="mt-0.5 flex flex-wrap items-center justify-between gap-2">
        <h3 className="m-0 text-lg font-semibold text-[#08060d]">{module.title}</h3>
        <div className="flex items-center gap-2">
          <Tag color={module.allow_retake ? 'blue' : 'default'} className="mr-0">
            {module.allow_retake ? 'Bisa diulang' : 'Sekali kerja'}
          </Tag>
          <span className="text-xs text-gray-500">
            {answeredCount}/{questions.length} terjawab
          </span>
        </div>
      </div>
      {module.description && (
        <p className="mt-1 whitespace-pre-line text-sm text-gray-600">{module.description}</p>
      )}

      {formattedDueAt && (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-gray-600">
          <ClockCircleOutlined />
          <span>
            Tenggat: <span className="font-medium">{formattedDueAt}</span>
          </span>
          {isPastDue && (
            <Tag color="red" className="mr-0">
              Lewat tenggat
            </Tag>
          )}
        </p>
      )}
      {isPastDue && module.late_penalty_percent > 0 && (
        <Alert
          className="mt-3"
          type="warning"
          showIcon
          message={`Lewat tenggat — poin berkurang ${module.late_penalty_percent}%`}
          description="Quiz tetap bisa disubmit, tetapi poin yang masuk leaderboard akan dipotong."
        />
      )}

      <div className="mt-4 space-y-6">
        {questions.map((question, index) => {
          const answer = answers[question.id]
          const saving = savingIds.has(question.id)

          if (question.question_type === 'essai') {
            return (
              <div key={question.id}>
                <p className="text-sm font-medium text-[#08060d]">
                  <span className="mr-1 text-gray-400">{index + 1}.</span>
                  {question.question_text}
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    (essay{saving ? ' — menyimpan...' : ''})
                  </span>
                </p>
                <Input.TextArea
                  className="mt-2"
                  rows={4}
                  value={answer?.answer_text ?? ''}
                  onChange={(event) => handleEssayChange(question, event.target.value)}
                  onBlur={() => handleEssayBlur(question)}
                  placeholder="Tulis jawabanmu di sini..."
                />
              </div>
            )
          }

          return (
            <div key={question.id}>
              <p className="text-sm font-medium text-[#08060d]">
                <span className="mr-1 text-gray-400">{index + 1}.</span>
                {question.question_text}
                {saving && <span className="ml-2 text-xs font-normal text-gray-400">— menyimpan...</span>}
              </p>
              <Radio.Group
                className="mt-2 flex flex-col gap-2"
                value={answer?.question_option}
                onChange={(event) =>
                  handlePickOption(question, event.target.value as number)
                }
              >
                {question.options.map((option) => (
                  <Radio key={option.id} value={option.id} className="ml-0">
                    {option.option_text}
                  </Radio>
                ))}
              </Radio.Group>
            </div>
          )
        })}
      </div>

      <div className="sticky bottom-0 mt-6 flex items-center justify-between gap-3 border-t border-gray-200 bg-white pt-3">
        <span className="text-xs text-gray-500">
          {answeredCount === questions.length
            ? 'Semua soal sudah terjawab.'
            : `${questions.length - answeredCount} soal belum dijawab.`}
        </span>
        <Button
          type="primary"
          size="large"
          loading={submitting}
          disabled={savingIds.size > 0}
          onClick={handleSubmit}
        >
          Kumpulkan Jawaban
        </Button>
      </div>
    </div>
  )
}

function QuestionReview({
  index,
  question,
  answer,
}: {
  index: number
  question: Question
  answer: UserAnswer | undefined
}) {
  const answeredOption = answer?.question_option

  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <p className="text-sm font-medium text-[#08060d]">
        <span className="mr-1 text-gray-400">{index + 1}.</span>
        {question.question_text}
        {question.question_type === 'essai' && (
          <Tag className="ml-2 mr-0">Essay</Tag>
        )}
      </p>

      {question.question_type === 'essai' ? (
        <div className="mt-2 space-y-1">
          <p className="whitespace-pre-line rounded bg-gray-50 p-2 text-sm text-gray-700">
            {answer?.answer_text?.trim() || (
              <span className="italic text-gray-400">(jawaban kosong)</span>
            )}
          </p>
          {answer?.score != null && (
            <p className="text-xs text-gray-500">Skor essay: {answer.score}</p>
          )}
        </div>
      ) : (
        <ul className="mt-2 list-none space-y-1 p-0">
          {question.options.map((option) => {
            const chosen = answeredOption === option.id
            const correct = option.is_correct === true
            return (
              <li
                key={option.id}
                className={`flex items-center gap-2 text-sm ${
                  correct ? 'font-medium text-emerald-600' : 'text-gray-600'
                }`}
              >
                {correct ? (
                  <CheckCircleFilled className="text-emerald-500" />
                ) : chosen ? (
                  <CheckCircleOutlined className="text-gray-400" />
                ) : (
                  <span className="inline-block w-4" />
                )}
                <span>{option.option_text}</span>
                {chosen && <Tag className="mr-0">Jawabanmu</Tag>}
                {correct && <Tag color="green" className="mr-0">Benar</Tag>}
              </li>
            )
          })}
        </ul>
      )}

      {question.explanation && (
        <p className="mt-2 border-t border-gray-100 pt-2 text-xs text-gray-500">
          Pembahasan: {question.explanation}
        </p>
      )}
    </div>
  )
}
