import { useEffect, useState } from 'react'
import { Form, Modal, Select } from 'antd'

import {
  awardBadge,
  getFieldErrors,
  listEnrollments,
  notifyError,
  notifySuccess,
} from '@/api'
import { fetchAllPages } from '@/utils/paginate'
import type { Badge } from '@/types/badge'
import type { CourseEnrollment } from '@/types/enrollment'

interface AwardFormValues {
  user: number
}

interface AwardBadgeModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah diberikan — untuk refresh daftar penerima. */
  onAwarded: () => void
  badge: Badge | null
}

/**
 * Modal mentor memberi badge manual ke student yang enrolled di course
 * (POST /user-badge/). Hanya badge bertipe `manual`.
 */
export function AwardBadgeModal({
  open,
  onClose,
  onAwarded,
  badge,
}: AwardBadgeModalProps) {
  const [form] = Form.useForm<AwardFormValues>()
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
    }
  }

  useEffect(() => {
    if (!open || !badge) return
    let cancelled = false

    fetchAllPages((params) =>
      listEnrollments({ ...params, course: badge.course }),
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
  }, [open, badge])

  const handleSubmit = async (values: AwardFormValues) => {
    if (!badge) return
    setSubmitting(true)
    try {
      await awardBadge({ badge: badge.id, user: values.user })
      notifySuccess(`Badge "${badge.name}" awarded.`)
      onAwarded()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof AwardFormValues,
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
      title={badge ? `Award Badge: ${badge.name}` : 'Award Badge'}
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
      </Form>
    </Modal>
  )
}
