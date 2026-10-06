import {
  FileTextOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { Collapse } from 'antd'
import type { ReactNode } from 'react'

import type { CourseModule, ModuleCategory } from '@/types/course'

const categoryIcons: Record<ModuleCategory, ReactNode> = {
  text: <FileTextOutlined />,
  video: <PlayCircleOutlined />,
  upload: <UploadOutlined />,
  quiz: <QuestionCircleOutlined />,
}

interface ModuleAccordionProps {
  modules: CourseModule[]
}

/** Daftar module course sebagai collapse — urut `sequence`, ikon per kategori. */
export function ModuleAccordion({ modules }: ModuleAccordionProps) {
  const sorted = [...modules].sort(
    (a, b) => (a.sequence ?? Number.MAX_SAFE_INTEGER) - (b.sequence ?? Number.MAX_SAFE_INTEGER),
  )

  return (
    <Collapse
      items={sorted.map((module) => ({
        key: module.id,
        label: (
          <span className="flex items-center gap-3">
            <span className="text-[#1677ff]">{categoryIcons[module.module_category]}</span>
            <span className="font-medium text-[#08060d]">{module.title}</span>
          </span>
        ),
        children: module.description ? (
          <p className="whitespace-pre-line leading-relaxed text-gray-600">
            {module.description}
          </p>
        ) : null,
        disabled: !module.description,
      }))}
    />
  )
}
