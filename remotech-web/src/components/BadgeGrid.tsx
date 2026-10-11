import { Empty, Skeleton } from 'antd'
import { useEffect, useState } from 'react'

import { BadgeCard } from './BadgeCard'
import { BadgeDetailModal } from './BadgeDetailModal'
import { getMyBadges, notifyError } from '@/api'
import type { MyBadgeEntry } from '@/types/badge'

interface BadgeGridProps {
  /** Batasi ke satu course; kosong = semua course yang di-enroll. */
  course?: number
  /** Hanya tampilkan badge yang sudah didapat (mis. showcase profil). */
  earnedOnly?: boolean
  /** Tampilkan judul course pada tiap kartu. */
  showCourse?: boolean
  /** Nomor ulang saat berubah (mis. setelah submit module) untuk reload. */
  reloadKey?: number
}

/**
 * Grid badge milik user: earned (warna penuh) + locked (grayscale, progres x/y).
 * Data dari GET /user-badge/me/.
 */
export function BadgeGrid({
  course,
  earnedOnly = false,
  showCourse = false,
  reloadKey = 0,
}: BadgeGridProps) {
  // Null = belum termuat (menampilkan skeleton); reload mengganti isi tanpa
  // kembali ke skeleton agar tidak berkedip.
  const [entries, setEntries] = useState<MyBadgeEntry[] | null>(null)
  // Entry yang kartunya diklik (modal detail); null = tertutup.
  const [detail, setDetail] = useState<MyBadgeEntry | null>(null)

  useEffect(() => {
    let cancelled = false

    getMyBadges(course)
      .then((data) => {
        if (!cancelled) setEntries(data)
      })
      .catch((error) => {
        if (!cancelled) {
          setEntries([])
          notifyError(error)
        }
      })

    return () => {
      cancelled = true
    }
  }, [course, reloadKey])

  if (entries === null) {
    return <Skeleton active paragraph={{ rows: 2 }} />
  }

  const visible = earnedOnly ? entries.filter((entry) => entry.earned) : entries

  if (visible.length === 0) {
    return (
      <Empty
        description={
          earnedOnly
            ? 'Belum ada badge yang didapat.'
            : 'Belum ada badge di course yang kamu ikuti.'
        }
        className="py-8"
      />
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {visible.map((entry) => (
        <BadgeCard
          key={entry.badge.id}
          badge={entry.badge}
          earned={entry.earned}
          progress={entry.progress}
          showCourse={showCourse}
          onClick={() => setDetail(entry)}
        />
      ))}
      {detail && (
        <BadgeDetailModal entry={detail} onClose={() => setDetail(null)} />
      )}
    </div>
  )
}
