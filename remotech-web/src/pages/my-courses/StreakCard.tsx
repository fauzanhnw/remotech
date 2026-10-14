import { FireOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'

import { getWeeklyActivity } from '@/api'
import type { WeeklyActivity } from '@/types/progress'

const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const EMPTY_ACTIVITY: WeeklyActivity = {
  days: [],
  current_streak: 0,
  best_streak: 0,
  week_active_count: 0,
}

interface DisplayDay {
  key: string
  label: string
  active: boolean
  count: number
  isToday: boolean
}

/**
 * Kartu streak belajar 7 hari (dihitung backend, zona WIB).
 * Saat API gagal kartu tetap tampil dengan angka 0 tanpa toast.
 */
export function StreakCard() {
  const [activity, setActivity] = useState<WeeklyActivity>(EMPTY_ACTIVITY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    getWeeklyActivity()
      .then((data) => {
        if (!cancelled) setActivity(data)
      })
      .catch(() => {
        // Senyap: kartu tetap tampil dengan streak 0.
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const displayDays: DisplayDay[] =
    activity.days.length === WEEKDAY_LABELS.length
      ? activity.days.map((day, index) => ({
          key: day.date,
          label: WEEKDAY_LABELS[day.weekday] ?? '',
          active: day.active,
          count: day.count,
          isToday: index === activity.days.length - 1,
        }))
      : WEEKDAY_LABELS.map((label, index) => ({
          key: label,
          label,
          active: false,
          count: 0,
          isToday: index === WEEKDAY_LABELS.length - 1,
        }))

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-orange-50">
          <FireOutlined className="text-xl text-orange-500" />
        </span>
        <div>
          <p className="text-2xl font-bold leading-none text-[#08060d]">
            {loading ? '–' : activity.current_streak}
            <span className="ml-2 text-sm font-medium text-gray-500">
              Day Streak
            </span>
          </p>
          <p className="mt-2 text-xs text-gray-500">
            {loading
              ? 'Loading study activity...'
              : `${activity.week_active_count}/7 active days this week · Best streak ${activity.best_streak} days`}
          </p>
        </div>
      </div>

      <div className="flex flex-col items-start gap-1.5 sm:items-end">
        <span className="text-xs text-gray-400">Last 7 days</span>
        <div
          className="flex items-end gap-2"
          role="img"
          aria-label={`7-day activity chart, ${activity.week_active_count} active days`}
        >
          {displayDays.map((day) => (
            <div key={day.key} className="flex flex-col items-center gap-1.5">
              <span
                title={day.active ? `${day.count} activities` : 'No activity'}
                className={`block h-4 w-4 rounded-full ${
                  day.active ? 'bg-orange-500' : 'bg-gray-200'
                }${day.isToday ? ' ring-2 ring-orange-300 ring-offset-1' : ''}`}
              />
              <span
                className={`text-[11px] ${day.isToday ? 'font-semibold text-[#08060d]' : 'text-gray-500'}`}
              >
                {day.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
