import { UploadOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import { Button, Form, Input, InputNumber, Modal, Switch, Upload } from 'antd'
import { useEffect, useState } from 'react'

import { createCourse, getFieldErrors, notifyError, notifySuccess } from '@/api'

interface AddCourseValues {
  title: string
  description?: string
  price?: number
  thumbnail?: UploadFile[]
  is_publish?: boolean
  is_open?: boolean
}

interface AddCourseModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah course berhasil dibuat — untuk refresh daftar. */
  onCreated: () => void
}

/** Sinkronkan event Upload (atau array biasa) menjadi `fileList` Form. */
function toFileList(event: unknown): UploadFile[] {
  if (Array.isArray(event)) return event as UploadFile[]
  if (event && typeof event === 'object' && 'fileList' in event) {
    return (event as { fileList?: UploadFile[] }).fileList ?? []
  }
  return []
}

/** Modal pembuatan course: judul, deskripsi, harga, thumbnail, publish/open. */
export function AddCourseModal({ open, onClose, onCreated }: AddCourseModalProps) {
  const [form] = Form.useForm<AddCourseValues>()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) form.resetFields()
  }, [open, form])

  const handleSubmit = async (values: AddCourseValues) => {
    setSubmitting(true)
    try {
      const thumbnail = values.thumbnail?.[0]?.originFileObj
      await createCourse({
        title: values.title,
        description: values.description,
        price: values.price ?? 0,
        is_publish: values.is_publish ?? false,
        is_open: values.is_open ?? false,
        thumbnail,
      })
      notifySuccess('Course berhasil dibuat.')
      onCreated()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof AddCourseValues,
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
      title="Add Course"
      okText="Create"
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <Form<AddCourseValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        initialValues={{ price: 0, is_publish: false, is_open: false }}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Title"
          name="title"
          rules={[{ required: true, message: 'Title is required' }]}
        >
          <Input placeholder="Judul course" maxLength={200} />
        </Form.Item>

        <Form.Item label="Description" name="description">
          <Input.TextArea rows={4} placeholder="Deskripsi singkat course" />
        </Form.Item>

        <Form.Item
          label="Price"
          name="price"
          rules={[{ required: true, message: 'Price is required' }]}
        >
          <InputNumber min={0} step={10000} placeholder="0 = gratis" className="w-full" />
        </Form.Item>

        <Form.Item
          label="Thumbnail"
          name="thumbnail"
          valuePropName="fileList"
          getValueFromEvent={toFileList}
        >
          <Upload accept="image/*" maxCount={1} listType="picture" beforeUpload={() => false}>
            <Button icon={<UploadOutlined />}>Select image</Button>
          </Upload>
        </Form.Item>

        <div className="flex flex-wrap gap-10">
          <Form.Item
            label="Publish"
            name="is_publish"
            valuePropName="checked"
            extra="Tampil di katalog publik."
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="Open for enrollment"
            name="is_open"
            valuePropName="checked"
            extra="Penerimaan pembelian baru."
          >
            <Switch />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  )
}
