import { useEffect, useState } from 'react'
import { Form, Input, InputNumber, Modal, Select } from 'antd'

import {
  createPointBonus,
  getFieldErrors,
  listEnrollments,
  notifyError,
  notifySuccess,
} from '@/api'
import { fetchAllPages } from '@/utils/paginate'
import type { CourseEnrollment } from '@/types/enrollment'

interface BonusFormValues {
  user: number
  point: number
  description: string
}

interface AddPointBonusModalProps {
  open: boolean
  /** Course yang sedang dipilih di halaman leaderboard mentor. */
  courseId: number
  onClose: () => void
  /** Dipanggil setelah bonus diberikan — untuk refresh papan & riwayat. */
  onGranted: () => void
  /** Opsional — user id student yang sudah ter-pra-isi (dari baris leaderboard). */
  initialUser?: number
}

/**
 * Modal mentor memberi bonus poin manual ke student enrolled
 * (POST /point-bonus/). Poin minimal 1; deskripsi wajib.
 */
export function AddPointBonusModal({
  open,
  courseId,
  onClose,
  onGranted,
  initialUser,
}: AddPointBonusModalProps) {
  const [form] = Form.useForm<BonusFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([])
  const [loading, setLoading] = useState(false)

  // Reset state saat modal dibuka (pola "adjusting state when a prop changes").
  const [prevOpen, setPrevOpen] = useState(open)
  if (prevOpen !== open) {
    setPrevOpen(open)
    if (open) {
      setEnrollments([])
      setLoading(true)
      form.resetFields()
      if (initialUser != null) {
        form.setFieldsValue({ user: initialUser })
      }
    }
  }

  useEffect(() => {
    if (!open) return
    let cancelled = false

    fetchAllPages((params) =>
      listEnrollments({ ...params, course: courseId }),
    )
      .then((items) => {
        if (!cancelled) setEnrollments(items)
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
  }, [open, courseId])

  const handleSubmit = async (values: BonusFormValues) => {
    setSubmitting(true)
    try {
      await createPointBonus({ course: courseId, ...values })
      notifySuccess('Point bonus awarded.')
      onGranted()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof BonusFormValues,
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
      title="Add Manual Points"
      okText="Award"
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={480}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={(values) => void handleSubmit(values)}
      >
        <Form.Item
          label="Student"
          name="user"
          rules={[{ required: true, message: 'Select a student first' }]}
        >
          <Select
            showSearch
            loading={loading}
            placeholder="Search enrolled students..."
            optionFilterProp="label"
            options={enrollments.map((row) => ({
              value: row.user,
              label: row.user_name,
            }))}
          />
        </Form.Item>
        <Form.Item
          label="Points"
          name="point"
          rules={[{ required: true, message: 'Enter the number of points' }]}
        >
          <InputNumber min={1} placeholder="50" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          label="Reason"
          name="description"
          rules={[{ required: true, message: 'Enter the reason for awarding points' }]}
        >
          <Input placeholder="e.g. Outstanding contribution in the discussion" maxLength={255} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
