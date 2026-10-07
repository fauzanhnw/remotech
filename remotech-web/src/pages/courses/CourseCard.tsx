import { PictureOutlined } from '@ant-design/icons'
import { Tag } from 'antd'
import { Link } from 'react-router-dom'

import type { Course } from '@/types/course'
import { formatRupiah } from '@/utils/format'

interface CourseCardProps {
  course: Course
  /** Tujuan link kartu — default `/courses/{id}` (katalog publik). */
  to?: string
}

/** Kartu katalog: thumbnail, judul, uploader, tag ketersediaan, harga. */
export function CourseCard({ course, to }: CourseCardProps) {
  return (
    <Link
      to={to ?? `/courses/${course.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-white no-underline shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="aspect-video overflow-hidden bg-gray-100">
        {course.thumbnail ? (
          <img
            src={course.thumbnail}
            alt={course.title}
            loading="lazy"
            className="h-full w-full object-cover transition group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-4xl text-gray-300">
            <PictureOutlined />
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="line-clamp-2 font-semibold text-[#08060d]">{course.title}</h3>
        <p className="text-sm text-gray-500">{course.user_name}</p>

        <div className="mt-auto flex items-center justify-between pt-3">
          <Tag color={course.is_open ? 'green' : 'red'} className="mr-0">
            {course.is_open ? 'Open' : 'Closed'}
          </Tag>
          <span
            className={`font-semibold ${course.price <= 0 ? 'text-emerald-600' : 'text-[#08060d]'}`}
          >
            {formatRupiah(course.price)}
          </span>
        </div>
      </div>
    </Link>
  )
}
