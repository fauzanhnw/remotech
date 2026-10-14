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
        notifySuccess('Assignment updated.')
      } else {
        await createAssignment(payload)
        notifySuccess('Assignment created.')
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
      title={editing ? 'Edit Assignment' : 'Create Assignment'}
      okText={editing ? 'Save' : 'Create'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={640}
    >
      <p className="mb-4 text-sm text-gray-500">
        Module: <span className="font-medium text-gray-700">{module?.title}</span>
        {' — students submit their work links for this assignment.'}
      </p>

      <Form<AssignmentFormValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Assignment Name"
          name="name"
          rules={[{ required: true, message: 'Assignment name is required' }]}
        >
          <Input placeholder="e.g. Assignment 1 — Case Study Analysis" allowClear />
        </Form.Item>

        <Form.Item
          label="Description / Instructions"
          name="description"
          rules={[{ required: true, message: 'Assignment description is required' }]}
        >
          <Input.TextArea
            rows={5}
            placeholder="Explain what students need to do and the submission format..."
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
