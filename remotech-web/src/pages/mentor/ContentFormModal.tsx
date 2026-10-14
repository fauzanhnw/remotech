import { useEffect, useState } from 'react'
import { Form, Input, Modal } from 'antd'

import {
  createModuleContent,
  getFieldErrors,
  notifyError,
  notifySuccess,
  updateModuleContent,
} from '@/api'
import type { ModuleContent } from '@/types/content'
import type { CourseModule } from '@/types/course'
import { RichTextEditor } from './RichTextEditor'

interface ContentFormValues {
  content_text?: string
  content_url?: string
}

interface ContentFormModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah konten tersimpan — untuk refresh daftar. */
  onSaved: () => void
  module: CourseModule | null
  /** Diisi saat mengedit konten exist. */
  content?: ModuleContent | null
}

/** Modal create/edit konten module — form mengikuti kategori module. */
export function ContentFormModal({
  open,
  onClose,
  onSaved,
  module,
  content,
}: ContentFormModalProps) {
  const [form] = Form.useForm<ContentFormValues>()
  const [submitting, setSubmitting] = useState(false)
  const editing = Boolean(content)
  const category = module?.module_category ?? 'text'
  const needsUrl = category === 'video' || category === 'upload'

  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (content) {
      form.setFieldsValue({
        content_text: content.content_text,
        content_url: content.content_url,
      })
    }
  }, [open, content, form])

  const handleSubmit = async (values: ContentFormValues) => {
    if (!module) return
    setSubmitting(true)
    try {
      const payload = needsUrl
        ? { content_url: values.content_url }
        : { content_text: values.content_text }

      if (content) {
        await updateModuleContent(content.id, payload, {
          meta: { suppressErrorToast: true },
        })
        notifySuccess('Content updated.')
      } else {
        await createModuleContent(
          { ...payload, module: module.id },
          { meta: { suppressErrorToast: true } },
        )
        notifySuccess('Content added.')
      }
      onSaved()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof ContentFormValues,
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
      title={editing ? 'Edit Content' : 'Add Content'}
      okText={editing ? 'Save' : 'Add'}
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
      width={720}
    >
      <p className="mb-4 text-sm text-gray-500">
        Module: <span className="font-medium text-gray-700">{module?.title}</span>
        {' — '}
        category <span className="font-medium text-gray-700">{category}</span>
      </p>

      <Form<ContentFormValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        {needsUrl ? (
          <Form.Item
            label="Content URL"
            name="content_url"
            rules={[
              { required: true, message: 'Content URL is required' },
              { type: 'url', message: 'Enter a valid URL' },
            ]}
          >
            <Input
              placeholder="https://www.youtube.com/watch?v=... or https://.../media/..."
              allowClear
            />
          </Form.Item>
        ) : (
          <Form.Item
            label="Content"
            name="content_text"
            rules={[
              {
                validator: (_, value: string | undefined) => {
                  if (category === 'text' && !(value ?? '').trim()) {
                    return Promise.reject(new Error('Content is required'))
                  }
                  return Promise.resolve()
                },
              },
            ]}
          >
            <RichTextEditor placeholder="Write the module material here (HTML allowed)..." />
          </Form.Item>
        )}
      </Form>
    </Modal>
  )
}
