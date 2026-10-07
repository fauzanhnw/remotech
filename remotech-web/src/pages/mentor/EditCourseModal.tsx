import { UploadOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'
import { Button, Form, Input, InputNumber, Modal, Switch, Upload } from 'antd'
import { useEffect, useState } from 'react'

import { getFieldErrors, notifyError, notifySuccess, updateCourse } from '@/api'
import type { Course, CourseUpdate } from '@/types/course'

interface EditCourseValues {
  title: string
  description?: string
  price?: number
  thumbnail?: UploadFile[]
  is_publish?: boolean
  is_open?: boolean
}

interface EditCourseModalProps {
  open: boolean
  onClose: () => void
  /** Dipanggil setelah course berhasil diperbarui — untuk refresh data. */
  onSaved: () => void
  course: Course
}

/** uid untuk pratinjau thumbnail lama — dipakai untuk mendeteksi perubahan. */
const INITIAL_THUMB_UID = 'existing-thumbnail'

/** Sinkronkan event Upload (atau array biasa) menjadi `fileList` Form. */
function toFileList(event: unknown): UploadFile[] {
  if (Array.isArray(event)) return event as UploadFile[]
  if (event && typeof event === 'object' && 'fileList' in event) {
    return (event as { fileList?: UploadFile[] }).fileList ?? []
  }
  return []
}

/** Modal edit course: judul, deskripsi, harga, thumbnail (ganti/hapus), publish/open. */
export function EditCourseModal({ open, onClose, onSaved, course }: EditCourseModalProps) {
  const [form] = Form.useForm<EditCourseValues>()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue({
      title: course.title,
      description: course.description,
      price: course.price,
      is_publish: course.is_publish,
      is_open: course.is_open,
      thumbnail: course.thumbnail
        ? [
            {
              uid: INITIAL_THUMB_UID,
              name: 'thumbnail',
              status: 'done',
              url: course.thumbnail,
            },
          ]
        : [],
    })
  }, [open, course, form])

  const handleSubmit = async (values: EditCourseValues) => {
    const payload: CourseUpdate = {
      title: values.title,
      description: values.description,
      price: values.price ?? 0,
      is_publish: values.is_publish ?? false,
      is_open: values.is_open ?? false,
    }

    const thumb = values.thumbnail?.[0]
    if (thumb?.originFileObj) {
      payload.thumbnail = thumb.originFileObj
    } else if (!thumb) {
      // File preview lama dihapus user tanpa ganti baru → hapus thumbnail.
      payload.thumbnail = ''
    }
    // Selain itu thumbnail tidak diubah (tidak dikirim).

    setSubmitting(true)
    try {
      await updateCourse(course.id, payload, { meta: { suppressErrorToast: true } })
      notifySuccess('Course berhasil diperbarui.')
      onSaved()
      onClose()
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof EditCourseValues,
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
      title="Edit Course"
      okText="Simpan"
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <Form<EditCourseValues>
        form={form}
        layout="vertical"
        requiredMark={false}
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
          extra="Klik X pada pratinjau untuk menghapus thumbnail."
        >
          <Upload
            accept="image/*"
            maxCount={1}
            listType="picture"
            beforeUpload={() => false}
          >
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
