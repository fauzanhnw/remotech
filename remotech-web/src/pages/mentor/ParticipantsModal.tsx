import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Empty, Input, Modal, Skeleton, Table, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'

import { listEnrollments, notifyError } from '@/api'
import type { CourseEnrollment } from '@/types/enrollment'
import { fetchAllPages } from '@/utils/paginate'

interface ParticipantsModalProps {
  open: boolean
  onClose: () => void
  /** Course yang pesertanya ditampilkan (null saat modal tertutup). */
  courseId: number | null
  courseTitle: string
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Modal mentor melihat daftar peserta yang enroll course miliknya
 * (`GET /enroll/?course={id}`, scoped ke pemilik course di backend).
 * Search by nama dilakukan client-side (semua baris di-fetch sekali).
 */
export function ParticipantsModal({
  open,
  onClose,
  courseId,
  courseTitle,
}: ParticipantsModalProps) {
  const [participants, setParticipants] = useState<CourseEnrollment[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  // Reset state saat modal dibuka (pola "adjusting state when a prop changes").
  const [prevOpen, setPrevOpen] = useState(open)
  if (prevOpen !== open) {
    setPrevOpen(open)
    if (open) {
      setParticipants([])
      setSearch('')
      setLoading(true)
    }
  }

  useEffect(() => {
    if (!open || courseId == null) return
    let cancelled = false

    fetchAllPages((params) => listEnrollments({ ...params, course: courseId }))
      .then((items) => {
        if (!cancelled) setParticipants(items)
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
  }, [open, courseId, reloadKey])

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return participants
    return participants.filter((row) =>
      row.user_name.toLowerCase().includes(query),
    )
  }, [participants, search])

  const columns: ColumnsType<CourseEnrollment> = [
    {
      title: '#',
      key: 'index',
      width: 56,
      render: (_, __, index) => (
        <span className="text-gray-500">{index + 1}</span>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (name: string) => (
        <span className="font-medium text-[#08060d]">{name}</span>
      ),
    },
    {
      title: 'Enrolled',
      dataIndex: 'enrolled_at',
      key: 'enrolled_at',
      render: (value: string) => formatDateTime(value),
    },
  ]

  return (
    <Modal
      open={open}
      title={`Participants — ${courseTitle}`}
      onCancel={onClose}
      footer={null}
      destroyOnHidden
      width={720}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Input
          allowClear
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="Search participant name..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w-xs"
        />
        <div className="flex items-center gap-2">
          {!loading && (
            <span className="text-sm text-gray-500">
              {participants.length} participant
              {participants.length === 1 ? '' : 's'}
            </span>
          )}
          <Tooltip title="Refresh">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={() => setReloadKey((value) => value + 1)}
            />
          </Tooltip>
        </div>
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 5 }} />
      ) : visible.length === 0 ? (
        <Empty
          description={
            participants.length === 0
              ? 'No participants have enrolled in this course yet.'
              : 'No participants match your search.'
          }
          className="py-10"
        />
      ) : (
        <Table<CourseEnrollment>
          rowKey="id"
          columns={columns}
          dataSource={visible}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          size="middle"
        />
      )}
    </Modal>
  )
}
