import { useState } from 'react'
import { Button, Form, Input, Modal, Select, Upload } from 'antd'
import { PictureOutlined } from '@ant-design/icons'

import {
  createBadge,
  getFieldErrors,
  notifyError,
  notifySuccess,
  updateBadge,
} from '@/api'
import { badgeIconNode, BADGE_ICON_GROUPS } from '@/components/badgeIcons'
import type { Badge, BadgeRuleType } from '@/types/badge'

interface BadgeFormValues {
  name: string
  description: string
  reward?: string
  rule_type: BadgeRuleType
  icon_name?: string
}

interface BadgeFormModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah tersimpan — untuk refresh daftar. */
  onSaved: () => void
  courseId: number
  /** Diisi saat mengedit badge yang sudah ada. */
  badge?: Badge | null
}

const iconOptions = BADGE_ICON_GROUPS.map((group) => ({
  label: group.label,
  options: group.values,
}))

/**
 * Modal create/edit badge course. Ikon: pilih preset (`icon_name`) atau
 * unggah gambar (`icon_image`, opsional — unggahan menang saat dirender).
 */
export function BadgeFormModal({
  open,
  onClose,
  onSaved,
  courseId,
  badge,
}: BadgeFormModalProps) {
  const [form] = Form.useForm<BadgeFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const [iconFile, setIconFile] = useState<File | null>(null)
  const editing = Boolean(badge)

  // Reset form + file saat modal dibuka (pola "adjusting state when a prop changes").
  const [prevOpen, setPrevOpen] = useState(open)
  if (prevOpen !== open) {
    setPrevOpen(open)
    if (open) {
      form.resetFields()
      setIconFile(null)
      if (badge) {
        form.setFieldsValue({
          name: badge.name,
          description: badge.description,
          reward: badge.reward || undefined,
          rule_type: badge.rule_type,
          icon_name: badge.icon_name || undefined,
        })
      }
    }
  }

  const handleSubmit = async (values: BadgeFormValues) => {
    setSubmitting(true)
    try {
      if (badge) {
        // FormData agar unggahan ikon (bila dipilih) ikut terkirim.
        const payload = new FormData()
        payload.append('name', values.name.trim())
        payload.append('description', values.description.trim())
        payload.append('reward', values.reward?.trim() ?? '')
        payload.append('rule_type', values.rule_type)
        payload.append('icon_name', values.icon_name ?? '')
        if (iconFile) payload.append('icon_image', iconFile)
        await updateBadge(badge.id, payload)
        notifySuccess('Badge updated.')
      } else if (iconFile) {
        const payload = new FormData()
        payload.append('course', String(courseId))
        payload.append('name', values.name.trim())
        payload.append('description', values.description.trim())
        payload.append('reward', values.reward?.trim() ?? '')
        payload.append('rule_type', values.rule_type)
        payload.append('icon_name', values.icon_name ?? '')
        payload.append('icon_image', iconFile)
        await createBadge(payload)
        notifySuccess('Badge created.')
      } else {
        await createBadge({
          course: courseId,
          name: values.name.trim(),
          description: values.description.trim(),
          reward: values.reward?.trim() ?? '',
          rule_type: values.rule_type,
          icon_name: values.icon_name ?? '',
        })
        notifySuccess('Badge created.')
      }
      onSaved()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof BadgeFormValues,
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
      title={editing ? 'Edit Badge' : 'Create Badge'}
      okText={editing ? 'Save' : 'Create'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={560}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={(values) => void handleSubmit(values)}
      >
        <Form.Item
          label="Badge name"
          name="name"
          rules={[{ required: true, message: 'Badge name is required' }]}
        >
          <Input placeholder="e.g. Graduate, Best Assignment" maxLength={100} />
        </Form.Item>
        <Form.Item
          label="Description"
          name="description"
          rules={[{ required: true, message: 'Description is required' }]}
        >
          <Input.TextArea rows={2} placeholder="Criteria or meaning of this badge" />
        </Form.Item>
        <Form.Item
          label="Reward"
          name="reward"
          extra="Reward earned along with this badge (optional)."
        >
          <Input.TextArea
            autoSize={{ minRows: 1, maxRows: 4 }}
            placeholder="e.g. Certificate + 1 month premium access"
          />
        </Form.Item>
        <Form.Item
          label="Type"
          name="rule_type"
          rules={[{ required: true, message: 'Badge type is required' }]}
          extra="Automatic: awarded by the system when all modules are complete; manual: awarded by the mentor."
        >
          <Select
            options={[
              { value: 'course_complete', label: 'Automatic — all modules completed' },
              { value: 'manual', label: 'Manual — awarded by mentor' },
            ]}
          />
        </Form.Item>
        <Form.Item label="Preset icon" name="icon_name">
          <Select
            allowClear
            placeholder="Select an icon (optional)"
            optionFilterProp="label"
            options={iconOptions}
            optionRender={(option) => (
              <span className="flex items-center gap-2">
                {badgeIconNode(String(option.value))}
                {option.label}
              </span>
            )}
          />
        </Form.Item>
        <Form.Item
          label="Upload icon (optional)"
          extra="If uploaded, this image takes precedence over the preset icon."
        >
          <Upload
            accept="image/*"
            maxCount={1}
            beforeUpload={(file) => {
              setIconFile(file)
              return false
            }}
            onRemove={() => setIconFile(null)}
            fileList={
              iconFile
                ? [{ uid: '-1', name: iconFile.name, status: 'done' as const }]
                : []
            }
          >
            <Button icon={<PictureOutlined />}>Choose image</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  )
}
