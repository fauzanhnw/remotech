import { useEffect, useState } from 'react'
import { Form, Input, Modal } from 'antd'

import {
  createAssignment,
  getFieldErrors,
  notifyError,
  notifySuccess,
  updateAssignment,
} from '@/api'
import type { Assignment, AssignmentCreate } from '@/types/content'
import type { CourseModule } from '@/types/course'

interface AssignmentFormValues {
  name: string
  description?: string
}

interface AssignmentFormModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah tersimpan — untuk refresh daftar. */
  onSaved: () => void
  module: CourseModule | null
  /** Diisi saat mengedit assignment yang sudah ada. */
  assignment?: Assignment | null
}

/**
 * Modal create/edit assignment (module `upload`) — tempat student
 * mengumpulkan tautan hasil kerja.
 */
export function AssignmentFormModal({
  open,
  onClose,
  onSaved,
  module,
  assignment,
}: AssignmentFormModalProps) {
  const [form] = Form.useForm<AssignmentFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const editing = Boolean(assignment)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (assignment) {
      form.setFieldsValue({
        name: assignment.name,
        description: assignment.description,
      })
    }
  }, [open, assignment, form])

  const handleSubmit = async (values: AssignmentFormValues) => {
    if (!module) return
    setSubmitting(true)
    try {
      const payload: AssignmentCreate = {
        course_module: module.id,
        name: values.name.trim(),
        description: (values.description ?? '').trim(),
      }

      if (assignment) {
        await updateAssignment(assignment.id, payload)
        notifySuccess('Tugas berhasil diperbarui.')
      } else {
        await createAssignment(payload)
        notifySuccess('Tugas berhasil dibuat.')
      }
      onSaved()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof AssignmentFormValues,
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

  return (
    <Modal
      open={open}
      title={editing ? 'Edit Tugas' : 'Buat Tugas'}
      okText={editing ? 'Simpan' : 'Buat'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={640}
    >
      <p className="mb-4 text-sm text-gray-500">
        Module: <span className="font-medium text-gray-700">{module?.title}</span>
        {' — student mengumpulkan tautan hasil kerja untuk tugas ini.'}
      </p>

      <Form<AssignmentFormValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Nama Tugas"
          name="name"
          rules={[{ required: true, message: 'Nama tugas wajib diisi' }]}
        >
          <Input placeholder="mis. Tugas 1 — Analisis Studi Kasus" allowClear />
        </Form.Item>

        <Form.Item
          label="Deskripsi / Instruksi"
          name="description"
          rules={[{ required: true, message: 'Deskripsi tugas wajib diisi' }]}
        >
          <Input.TextArea
            rows={5}
            placeholder="Jelaskan apa yang harus dikerjakan student dan format pengumpulannya..."
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
