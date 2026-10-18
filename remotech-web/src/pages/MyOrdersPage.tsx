import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Empty, Input, Select, Space, Table, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  checkPayment,
  listOrders,
  notifyError,
  notifySuccess,
  notifyWarning,
  payWithSnap,
} from '@/api'
import { usePageTitle } from '@/hooks/usePageTitle'
import type { CourseOrder, OrderStatus } from '@/types/order'
import { fetchAllPages } from '@/utils/paginate'
import { formatRupiah } from '@/utils/format'

type StatusFilter = 'all' | 'pending' | 'settlement' | 'failed'

const STATUS_META: Record<OrderStatus, { label: string; className: string }> = {
  settlement: { label: 'Successful', className: 'bg-emerald-50 text-emerald-600' },
  pending: { label: 'Pending payment', className: 'bg-amber-50 text-amber-600' },
  deny: { label: 'Denied', className: 'bg-red-50 text-red-600' },
  cancel: { label: 'Cancelled', className: 'bg-gray-100 text-gray-600' },
  expire: { label: 'Expired', className: 'bg-gray-100 text-gray-600' },
  failure: { label: 'Failed', className: 'bg-red-50 text-red-600' },
}

const FAILED_STATUSES: OrderStatus[] = ['deny', 'cancel', 'expire', 'failure']

function formatDate(value: string): string {
  return new Date(value).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatPaymentType(value: string): string {
  if (!value) return '—'
  return value.replaceAll('_', ' ')
}

/**
 * My Order: riwayat order pembelian course milik sendiri. Order yang masih
 * `pending` bisa dibayar langsung dari sini (Snap → cek pembayaran), yang
 * `settlement` menuju course terkait, dan yang gagal bisa dibeli ulang.
 */
export function MyOrdersPage() {
  usePageTitle('My Order')

  const [orders, setOrders] = useState<CourseOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [actingId, setActingId] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setReloadKey((value) => value + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const rows = await fetchAllPages((params) => listOrders(params))
        if (cancelled) return
        setOrders(
          [...rows].sort((a, b) => b.created_at.localeCompare(a.created_at)),
        )
      } catch (error) {
        if (!cancelled) notifyError(error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const applyOrder = (updated: CourseOrder) => {
    setOrders((rows) =>
      rows.map((row) => (row.id === updated.id ? updated : row)),
    )
  }

  const handleCheck = async (order: CourseOrder) => {
    setActingId(order.id)
    try {
      const updated = await checkPayment(order.id)
      applyOrder(updated)
      if (updated.transaction_status === 'settlement') {
        notifySuccess('Payment successful! The course is now in your learning list.')
      } else {
        notifyWarning(
          `Payment status: "${STATUS_META[updated.transaction_status].label}".`,
        )
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setActingId(null)
    }
  }

  const handlePay = async (order: CourseOrder) => {
    setActingId(order.id)
    try {
      if (!order.snap_token) {
        await handleCheck(order)
        return
      }

      const snapResult = await payWithSnap(order.snap_token)
      const updated = await checkPayment(order.id)
      applyOrder(updated)

      if (updated.transaction_status === 'settlement') {
        notifySuccess('Payment successful! The course is now in your learning list.')
      } else if (snapResult.status === 'error') {
        notifyError('Payment failed. Please try again.')
      } else {
        notifyWarning(
          `Payment is still "${STATUS_META[updated.transaction_status].label}". Please check again later.`,
        )
      }
    } catch (error) {
      notifyError(error)
    } finally {
      setActingId(null)
    }
  }

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    return orders.filter((order) => {
      if (statusFilter === 'pending' && order.transaction_status !== 'pending') {
        return false
      }
      if (
        statusFilter === 'settlement' &&
        order.transaction_status !== 'settlement'
      ) {
        return false
      }
      if (
        statusFilter === 'failed' &&
        !FAILED_STATUSES.includes(order.transaction_status)
      ) {
        return false
      }
      if (
        query &&
        !order.order_no.toLowerCase().includes(query) &&
        !order.course_title.toLowerCase().includes(query)
      ) {
        return false
      }
      return true
    })
  }, [orders, search, statusFilter])

  const pendingCount = useMemo(
    () => orders.filter((order) => order.transaction_status === 'pending').length,
    [orders],
  )

  const renderActions = (order: CourseOrder) => {
    if (order.transaction_status === 'pending') {
      return (
        <Space size={4}>
          <Button
            size="small"
            type="primary"
            loading={actingId === order.id}
            onClick={() => void handlePay(order)}
          >
            Pay
          </Button>
          <Button
            size="small"
            loading={actingId === order.id}
            onClick={() => void handleCheck(order)}
          >
            Check status
          </Button>
        </Space>
      )
    }

    if (order.transaction_status === 'settlement') {
      return (
        <Link
          to={`/my-courses/${order.course}`}
          className="text-sm text-blue-600 no-underline hover:underline"
        >
          View course
        </Link>
      )
    }

    return (
      <Link
        to={`/courses/${order.course}`}
        className="text-sm text-blue-600 no-underline hover:underline"
      >
        Buy again
      </Link>
    )
  }

  const columns: ColumnsType<CourseOrder> = [
    {
      title: 'No. Order',
      dataIndex: 'order_no',
      key: 'order_no',
      render: (orderNo: string) => <span className="font-mono text-xs">{orderNo}</span>,
    },
    {
      title: 'Course',
      key: 'course',
      render: (_, order) => (
        <Link
          to={
            order.transaction_status === 'settlement'
              ? `/my-courses/${order.course}`
              : `/courses/${order.course}`
          }
          className="font-medium text-blue-600 no-underline hover:underline"
        >
          {order.course_title}
        </Link>
      ),
    },
    {
      title: 'Amount',
      dataIndex: 'gross_amount',
      key: 'gross_amount',
      align: 'right',
      render: (amount: string) => formatRupiah(Number(amount)),
    },
    {
      title: 'Method',
      dataIndex: 'payment_type',
      key: 'payment_type',
      render: (value: string) => formatPaymentType(value),
    },
    {
      title: 'Date',
      key: 'created_at',
      render: (_, order) => (
        <div>
          <div>{formatDate(order.created_at)}</div>
          {order.paid_at && (
            <div className="text-xs text-gray-500">
              Paid {formatDate(order.paid_at)}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, order) => (
        <span
          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_META[order.transaction_status].className}`}
        >
          {STATUS_META[order.transaction_status].label}
        </span>
      ),
    },
    {
      title: '',
      key: 'actions',
      render: (_, order) => renderActions(order),
    },
  ]

  const emptyDescription = () => {
    if (orders.length === 0) return "You don't have any orders yet."
    if (search.trim()) return 'No orders match your search.'
    return 'No orders for this filter.'
  }

  return (
    <section className="mx-auto max-w px-4 py-10 pb-16 md:mx-8 xl:px-16">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#08060d]">My Order</h1>
          <p className="mt-2 text-gray-600">
            Course purchase history
            {pendingCount > 0 && (
              <span className="ml-1 font-medium text-amber-600">
                {pendingCount} pending payment
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap sm:flex-nowrap gap-3">
        <Input
          allowClear
          prefix={<SearchOutlined className="text-gray-400" />}
          placeholder="Search order no. or course title..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="max-w"
        />
        <Space className="flex flex-wrap sm:flex-nowrap">
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'all', label: 'All statuses' },
              { value: 'pending', label: 'Pending payment' },
              { value: 'settlement', label: 'Successful' },
              { value: 'failed', label: 'Failed/Denied' },
            ]}
            style={{ width: 180 }}
          />
          <Tooltip title="Refresh">
            <Button icon={<ReloadOutlined />} onClick={() => void load()} />
          </Tooltip>
        </Space>
      </div>

      {!loading && visible.length === 0 ? (
        <Empty description={emptyDescription()} className="py-16">
          {orders.length === 0 && (
            <Link to="/courses" className="inline-flex">
              <Button type="primary">Browse Catalog</Button>
            </Link>
          )}
        </Empty>
      ) : (
        <Table<CourseOrder>
          rowKey="id"
          columns={columns}
          dataSource={visible}
          loading={loading}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          scroll={{ x: 900 }}
        />
      )}
    </section>
  )
}
