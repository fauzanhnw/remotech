/** Konfigurasi menu sidebar dashboard mentor. */

import { BookOutlined, FileTextOutlined, TrophyOutlined } from '@ant-design/icons'
import type { ElementType } from 'react'

export interface MentorMenuItem {
  key: string
  label: string
  to: string
  icon: ElementType
}

export const mentorMenuItems: MentorMenuItem[] = [
  { key: 'courses', label: 'Courses', to: '/mentor/courses', icon: BookOutlined },
  {
    key: 'assignments',
    label: 'Assignments',
    to: '/mentor/assignments',
    icon: FileTextOutlined,
  },
  {
    key: 'leaderboard',
    label: 'Leaderboard',
    to: '/mentor/leaderboard',
    icon: TrophyOutlined,
  },
]
