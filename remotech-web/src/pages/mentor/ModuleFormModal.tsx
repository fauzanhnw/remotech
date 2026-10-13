import { useEffect, useState } from 'react'
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'

import {
  createModule,
  getFieldErrors,
  notifyError,
  notifySuccess,
  updateModule,
} from '@/api'
import type { CourseModule, ModuleCategory } from '@/types/course'

interface ModuleFormValues {
  title: string
  description?: string
  module_category: ModuleCategory
  point: number
  due_at?: Dayjs | null
  late_penalty_percent?: number
}

interface ModuleFormModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah module tersimpan — untuk refresh daftar. */
  onSaved: () => void
  courseId: number
  /** Diisi saat mengedit module exist. */
  module?: CourseModule | null
}

const CATEGORY_OPTIONS = [
  { value: 'text', label: 'Text' },
  { value: 'video', label: 'Video' },
  { value: 'upload', label: 'Upload' },
  { value: 'quiz', label: 'Quiz' },
]

/** Kategori yang mendukung tenggat pengumpulan + penalti keterlambatan. */
const DUE_AT_CATEGORIES: ModuleCategory[] = ['upload', 'quiz']

/** Modal create/edit module: judul, deskripsi, kategori, poin, tenggat. */
export function ModuleFormModal({
  open,
  onClose,
  onSaved,
  courseId,
  module,
}: ModuleFormModalProps) {
  const [form] = Form.useForm<ModuleFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const editing = Boolean(module)
  const category = Form.useWatch('module_category', form)
  const showDueAt = category != null && DUE_AT_CATEGORIES.includes(category)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (module) {
      form.setFieldsValue({
        title: module.title,
        description: module.description,
        module_category: module.module_category,
        point: module.point,
        late_penalty_percent: module.late_penalty_percent,
        // Backend mengirim ISO string; terima apa adanya (null bila kosong).
        due_at: module.due_at ? dayjs(module.due_at) : null,
      })
    }
  }, [open, module, form])

  const handleSubmit = async (values: ModuleFormValues) => {
    setSubmitting(true)
    try {
      const supportsDueAt =
        values.module_category != null &&
        DUE_AT_CATEGORIES.includes(values.module_category)
      const payload = {
        title: values.title,
        description: values.description,
        module_category: values.module_category,
        point: values.point,
        // Tenggat hanya dikirim untuk kategori upload/quiz; konversi ke ISO.
        due_at: supportsDueAt ? (values.due_at?.toISOString() ?? null) : null,
        late_penalty_percent: supportsDueAt
          ? (values.late_penalty_percent ?? 50)
          : undefined,
      }
      if (module) {
        // sequence & sengaja tidak dikirim: urutan hanya lewat tombol ↑↓.
        await updateModule(module.id, payload, {
          meta: { suppressErrorToast: true },
        })
        notifySuccessAndUpdate('Module berhasil diperbarui.')
      } else {
        await createModule(
          { ...payload, course: courseId },
          { meta: { suppressErrorToast: true } },
        )
        notifySuccessAndUpdate('Module berhasil ditambahkan.')
      }
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof ModuleFormValues,
            errors: [help],
          })),
        )
      } else {
        notifyError(error)
      }
    } finally {
      setSubmitting(false)
    }
  }

  function notifySuccessAndUpdate(message: string) {
    notifySuccess(message)
    onSaved()
    onClose()
  }

  return (
    <Modal
      open={open}
      title={editing ? 'Edit Module' : 'Add Module'}
      okText={editing ? 'Simpan' : 'Tambah'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <Form<ModuleFormValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        initialValues={{
          module_category: 'text',
          point: 100,
          late_penalty_percent: 50,
        }}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Title"
          name="title"
          rules={[{ required: true, message: 'Title is required' }]}
        >
          <Input placeholder="Judul module" maxLength={255} />
        </Form.Item>

        <Form.Item label="Description" name="description">
          <Input.TextArea rows={3} placeholder="Deskripsi singkat module" />
        </Form.Item>

        <div className="flex flex-wrap gap-4">
          <Form.Item label="Category" name="module_category">
            <Select className="w-44" options={CATEGORY_OPTIONS} />
          </Form.Item>

          <Form.Item
            label="Point"
            name="point"
            rules={[{ required: true, message: 'Point is required' }]}
          >
            <InputNumber min={0} className="w-36" />
          </Form.Item>
        </div>

        {showDueAt && (
          <div className="flex flex-wrap gap-4">
            <Form.Item
              label="Tenggat Pengumpulan"
              name="due_at"
              tooltip="Opsional — submit setelah tenggat diterima dengan pengurangan poin."
            >
              <DatePicker
                showTime
                format="DD MMM YYYY HH:mm"
                placeholder="Tanpa tenggat"
                className="w-56"
                disabledDate={(date) => date.isBefore(dayjs().startOf('day'))}
              />
            </Form.Item>

            <Form.Item
              label="Penalti Keterlambatan (%)"
              name="late_penalty_percent"
              tooltip="Persen poin yang dipotong bila submit melewati tenggat."
            >
              <InputNumber min={0} max={100} className="w-36" />
            </Form.Item>
          </div>
        )}
      </Form>
    </Modal>
  )
}
