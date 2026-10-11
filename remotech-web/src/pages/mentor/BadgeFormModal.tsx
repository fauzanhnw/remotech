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
        payload.append('rule_type', values.rule_type)
        payload.append('icon_name', values.icon_name ?? '')
        if (iconFile) payload.append('icon_image', iconFile)
        await updateBadge(badge.id, payload)
        notifySuccess('Badge berhasil diperbarui.')
      } else if (iconFile) {
        const payload = new FormData()
        payload.append('course', String(courseId))
        payload.append('name', values.name.trim())
        payload.append('description', values.description.trim())
        payload.append('rule_type', values.rule_type)
        payload.append('icon_name', values.icon_name ?? '')
        payload.append('icon_image', iconFile)
        await createBadge(payload)
        notifySuccess('Badge berhasil dibuat.')
      } else {
        await createBadge({
          course: courseId,
          name: values.name.trim(),
          description: values.description.trim(),
          rule_type: values.rule_type,
          icon_name: values.icon_name ?? '',
        })
        notifySuccess('Badge berhasil dibuat.')
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
      title={editing ? 'Edit Badge' : 'Buat Badge'}
      okText={editing ? 'Simpan' : 'Buat'}
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
          label="Nama badge"
          name="name"
          rules={[{ required: true, message: 'Nama badge wajib diisi' }]}
        >
          <Input placeholder="Mis. Graduate, Best Assignment" maxLength={100} />
        </Form.Item>
        <Form.Item
          label="Deskripsi"
          name="description"
          rules={[{ required: true, message: 'Deskripsi wajib diisi' }]}
        >
          <Input.TextArea rows={2} placeholder="Syarat atau makna badge ini" />
        </Form.Item>
        <Form.Item
          label="Tipe"
          name="rule_type"
          rules={[{ required: true, message: 'Tipe badge wajib dipilih' }]}
          extra="Otomatis diberi sistem saat semua module selesai; manual diberi mentor."
        >
          <Select
            options={[
              { value: 'course_complete', label: 'Otomatis — semua module selesai' },
              { value: 'manual', label: 'Manual — diberi mentor' },
            ]}
          />
        </Form.Item>
        <Form.Item label="Ikon preset" name="icon_name">
          <Select
            allowClear
            placeholder="Pilih ikon (opsional)"
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
          label="Unggah ikon (opsional)"
          extra="Jika diunggah, gambar ini menang atas ikon preset."
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
            <Button icon={<PictureOutlined />}>Pilih gambar</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  )
}
