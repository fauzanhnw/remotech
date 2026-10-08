import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Radio, Select } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'

import {
  createQuestion,
  notifySuccess,
  notifyWarning,
  updateQuestion,
} from '@/api'
import type { Question, QuestionCreate, QuestionType } from '@/types/quiz'

interface OptionFormValue {
  option_text: string
  is_correct: boolean
}

interface QuestionFormValues {
  question_text: string
  question_type: QuestionType
  explanation?: string
  options?: OptionFormValue[]
}

interface QuestionFormModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah tersimpan — untuk refresh daftar soal. */
  onSaved: () => void
  module: number
  /** Diisi saat mengedit soal exist. */
  question?: Question | null
}

const TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: 'choices', label: 'Pilihan Ganda' },
  { value: 'boolean', label: 'Benar / Salah' },
  { value: 'essai', label: 'Essay' },
]

const BOOLEAN_OPTIONS: OptionFormValue[] = [
  { option_text: 'Benar', is_correct: true },
  { option_text: 'Salah', is_correct: false },
]

const emptyOptions = (): OptionFormValue[] => [
  { option_text: '', is_correct: false },
  { option_text: '', is_correct: false },
]

/**
 * Modal create/edit soal quiz (nested `options`). Soal terkunci otomatis
 * oleh backend begitu ada pengerjaan — error ditampilkan sebagai toast.
 */
export function QuestionFormModal({
  open,
  onClose,
  onSaved,
  module,
  question,
}: QuestionFormModalProps) {
  const [form] = Form.useForm<QuestionFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const editing = Boolean(question)
  const questionType = Form.useWatch('question_type', form) ?? 'choices'
  const watchedOptions = Form.useWatch('options', form)
  const isEssay = questionType === 'essai'
  const isBoolean = questionType === 'boolean'

  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (question) {
      form.setFieldsValue({
        question_text: question.question_text,
        question_type: question.question_type,
        explanation: question.explanation,
        options:
          question.question_type === 'essai'
            ? []
            : question.options.map((option) => ({
                option_text: option.option_text,
                is_correct: option.is_correct === true,
              })),
      })
    } else {
      form.setFieldsValue({ question_type: 'choices', options: emptyOptions() })
    }
  }, [open, question, form])

  const handleTypeChange = (type: QuestionType) => {
    if (type === 'essai') {
      form.setFieldsValue({ options: [] })
    } else if (type === 'boolean') {
      form.setFieldsValue({ options: BOOLEAN_OPTIONS.map((option) => ({ ...option })) })
    } else if ((form.getFieldValue('options') ?? []).length < 2) {
      form.setFieldsValue({ options: emptyOptions() })
    }
  }

  const handlePickCorrect = (index: number) => {
    const current =
      form.getFieldValue('options')?.map((option: OptionFormValue, i: number) => ({
        ...option,
        is_correct: i === index,
      })) ?? []
    form.setFieldsValue({ options: current })
  }

  const handleSubmit = async (values: QuestionFormValues) => {
    const options = (values.options ?? []).filter(
      (option) => option.option_text.trim().length > 0,
    )

    if (!isEssay && options.length < 2) {
      notifyWarning('Minimal 2 opsi jawaban wajib diisi.')
      return
    }

    setSubmitting(true)
    try {
      const payload: QuestionCreate = {
        module,
        question_text: values.question_text.trim(),
        question_type: questionType,
        explanation: (values.explanation ?? '').trim(),
        options: isEssay
          ? []
          : options.map((option) => ({
              option_text: option.option_text.trim(),
              is_correct: option.is_correct,
            })),
      }

      if (question) {
        await updateQuestion(question.id, payload)
        notifySuccess('Soal berhasil diperbarui.')
      } else {
        await createQuestion(payload)
        notifySuccess('Soal berhasil ditambahkan.')
      }
      onSaved()
      onClose()
    } catch {
      // Error (termasuk "sudah ada pengerjaan") sudah ditampilkan interceptor.
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      title={editing ? 'Edit Soal' : 'Tambah Soal'}
      okText={editing ? 'Simpan' : 'Tambah'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={720}
    >
      <Form<QuestionFormValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
        initialValues={{ question_type: 'choices', options: emptyOptions() }}
      >
        <Form.Item
          label="Tipe Soal"
          name="question_type"
          rules={[{ required: true, message: 'Tipe soal wajib dipilih' }]}
        >
          <Select options={TYPE_OPTIONS} onChange={handleTypeChange} />
        </Form.Item>

        <Form.Item
          label="Pertanyaan"
          name="question_text"
          rules={[{ required: true, message: 'Pertanyaan wajib diisi' }]}
        >
          <Input.TextArea rows={3} placeholder="Tulis pertanyaan di sini..." />
        </Form.Item>

        {!isEssay && (
          <Form.Item
            label="Opsi Jawaban"
            required
            validateStatus={optionsWithoutCorrect(watchedOptions) ? 'error' : undefined}
            help={
              optionsWithoutCorrect(watchedOptions)
                ? 'Tandai tepat satu opsi sebagai jawaban benar.'
                : undefined
            }
          >
            <Form.List name="options">
              {(fields, { add, remove }) => (
                <div className="space-y-2">
                  {fields.map((field, index) => (
                    <div key={field.key} className="flex items-start gap-2">
                      <Radio
                        checked={watchedOptions?.[index]?.is_correct === true}
                        disabled={isBoolean}
                        onChange={() => handlePickCorrect(index)}
                        className="mt-2 shrink-0"
                      >
                        <span className="sr-only">Jawaban benar</span>
                      </Radio>
                      <Form.Item
                        name={[field.name, 'option_text']}
                        rules={[
                          { required: true, message: 'Opsi jawaban wajib diisi' },
                        ]}
                        className="mb-0 flex-1"
                      >
                        <Input
                          placeholder={`Opsi ${index + 1}`}
                          disabled={isBoolean}
                          allowClear
                        />
                      </Form.Item>
                      {!isBoolean && fields.length > 2 && (
                        <Button
                          type="text"
                          danger
                          aria-label="Hapus opsi"
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      )}
                    </div>
                  ))}
                  {!isBoolean && (
                    <Button
                      type="dashed"
                      block
                      icon={<PlusOutlined />}
                      onClick={() => add({ option_text: '', is_correct: false })}
                    >
                      Tambah Opsi
                    </Button>
                  )}
                  <p className="text-xs text-gray-500">
                    Pilih radio pada opsi yang merupakan jawaban benar.
                  </p>
                </div>
              )}
            </Form.List>
          </Form.Item>
        )}

        <Form.Item
          label="Pembahasan (opsional)"
          name="explanation"
          extra="Ditampilkan ke student setelah hasil quiz final."
        >
          <Input.TextArea rows={2} placeholder="mis. Karena 2 + 2 = 4." />
        </Form.Item>
      </Form>
    </Modal>
  )
}

/** Ada opsi terisi tapi belum ada satu pun yang ditandai benar. */
function optionsWithoutCorrect(options: OptionFormValue[] | undefined): boolean {
  const filled = (options ?? []).filter((option) => option.option_text.trim().length > 0)
  return filled.length > 0 && !filled.some((option) => option.is_correct)
}
