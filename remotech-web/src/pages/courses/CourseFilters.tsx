import { FilterOutlined, SearchOutlined } from '@ant-design/icons'
import { Badge, Button, Dropdown, Input, Segmented, Select } from 'antd'

export type PriceFilter = 'all' | 'free' | 'paid'

export interface OrderOption<T extends string = string> {
  value: T
  label: string
}

interface CourseFiltersProps<T extends string = string> {
  search: string
  onSearchChange: (value: string) => void
  /** `undefined` diperbolehkan bila state ordering bersifat opsional. */
  ordering: T | undefined
  onOrderingChange: (value: T) => void
  /** Opsi urutan di dropdown filter — default urutan katalog (created_at/harga/judul). */
  orderOptions?: readonly OrderOption<T>[]
  /** Nilai ordering yang dianggap "tanpa filter" (badge tombol tetap default). */
  defaultOrdering?: T
  /** Sembunyikan blok "Harga" dengan tidak mengirim kedua prop ini. */
  priceFilter?: PriceFilter
  onPriceFilterChange?: (value: PriceFilter) => void
}

const DEFAULT_ORDER_OPTIONS: readonly OrderOption[] = [
  { value: '-created_at', label: 'Terbaru' },
  { value: 'price', label: 'Harga: Rendah ke Tinggi' },
  { value: '-price', label: 'Harga: Tinggi ke Rendah' },
  { value: 'title', label: 'Judul A-Z' },
]

const DEFAULT_ORDERING = '-created_at'

/** Baris pencarian + tombol ikon filter (dropdown harga & urutan) untuk katalog. */
export function CourseFilters<T extends string = string>({
  search,
  onSearchChange,
  ordering,
  onOrderingChange,
  orderOptions,
  defaultOrdering,
  priceFilter,
  onPriceFilterChange,
}: CourseFiltersProps<T>) {
  const options = orderOptions ?? (DEFAULT_ORDER_OPTIONS as readonly OrderOption<T>[])
  const inactiveOrdering = (defaultOrdering ?? DEFAULT_ORDERING) as T
  const showPrice =
    priceFilter !== undefined && onPriceFilterChange !== undefined
  const filterActive =
    (showPrice && priceFilter !== 'all') || ordering !== inactiveOrdering

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
            {showPrice && priceFilter !== undefined && (
              <>
                <p className="mb-2 text-sm font-semibold text-[#08060d]">Harga</p>
                <Segmented
                  block
                  value={priceFilter}
                  onChange={(value) => onPriceFilterChange?.(value as PriceFilter)}
                  options={[
                    { value: 'all', label: 'Semua' },
                    { value: 'free', label: 'Gratis' },
                    { value: 'paid', label: 'Berbayar' },
                  ]}
                />
              </>
            )}

            <p
              className={`${showPrice ? 'mt-4' : ''} mb-2 text-sm font-semibold text-[#08060d]`}
            >
              Urutkan
            </p>
            <Select
              value={ordering}
              onChange={(value) => onOrderingChange(value as T)}
              options={options.map((option) => ({ ...option }))}
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
