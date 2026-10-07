import { useEffect, useState } from 'react'
import { Form, Input, InputNumber, Modal, Select } from 'antd'

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

/** Modal create/edit module: judul, deskripsi, kategori, poin. */
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

  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (module) {
      form.setFieldsValue({
        title: module.title,
        description: module.description,
        module_category: module.module_category,
        point: module.point,
      })
    }
  }, [open, module, form])

  const handleSubmit = async (values: ModuleFormValues) => {
    setSubmitting(true)
    try {
      if (module) {
        // sequence & sengaja tidak dikirim: urutan hanya lewat tombol ↑↓.
        await updateModule(module.id, values, {
          meta: { suppressErrorToast: true },
        })
        notifySuccessAndUpdate('Module berhasil diperbarui.')
      } else {
        await createModule(
          { ...values, course: courseId },
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
        initialValues={{ module_category: 'text', point: 100 }}
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
      </Form>
    </Modal>
  )
}
