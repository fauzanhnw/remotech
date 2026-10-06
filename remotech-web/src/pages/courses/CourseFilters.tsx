import { FilterOutlined, SearchOutlined } from '@ant-design/icons'
import { Badge, Button, Dropdown, Input, Segmented, Select } from 'antd'

import type { CourseListParams } from '@/types/params'

export type PriceFilter = 'all' | 'free' | 'paid'

interface CourseFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  priceFilter: PriceFilter
  onPriceFilterChange: (value: PriceFilter) => void
  ordering: CourseListParams['ordering']
  onOrderingChange: (value: CourseListParams['ordering']) => void
}

const ORDER_OPTIONS = [
  { value: '-created_at', label: 'Terbaru' },
  { value: 'price', label: 'Harga: Rendah ke Tinggi' },
  { value: '-price', label: 'Harga: Tinggi ke Rendah' },
  { value: 'title', label: 'Judul A-Z' },
] as const

const DEFAULT_ORDERING: CourseListParams['ordering'] = '-created_at'

/** Baris pencarian + tombol ikon filter (dropdown harga & urutan) untuk katalog. */
export function CourseFilters({
  search,
  onSearchChange,
  priceFilter,
  onPriceFilterChange,
  ordering,
  onOrderingChange,
}: CourseFiltersProps) {
  const filterActive = priceFilter !== 'all' || ordering !== DEFAULT_ORDERING

  return (
    <div className="flex items-center gap-3">
      <Input
        allowClear
        prefix={<SearchOutlined className="text-gray-400" />}
        placeholder="Search course..."
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        className="w-full"
      />

      <Dropdown
        trigger={['click']}
        placement="bottomRight"
        dropdownRender={() => (
          <div className="w-80 rounded-xl border border-gray-200 bg-white p-4 shadow-lg">
            <p className="mb-2 text-sm font-semibold text-[#08060d]">Harga</p>
            <Segmented
              block
              value={priceFilter}
              onChange={(value) => onPriceFilterChange(value as PriceFilter)}
              options={[
                { value: 'all', label: 'Semua' },
                { value: 'free', label: 'Gratis' },
                { value: 'paid', label: 'Berbayar' },
              ]}
            />

            <p className="mt-4 mb-2 text-sm font-semibold text-[#08060d]">Urutkan</p>
            <Select
              value={ordering}
              onChange={(value) => onOrderingChange(value)}
              options={ORDER_OPTIONS.map((option) => ({ ...option }))}
              className="w-full"
            />
          </div>
        )}
      >
        <Badge dot={filterActive} offset={[-4, 4]}>
          <Button
            type={filterActive ? 'primary' : 'default'}
            icon={<FilterOutlined />}
            aria-label="Filter"
          />
        </Badge>
      </Dropdown>
    </div>
  )
}
