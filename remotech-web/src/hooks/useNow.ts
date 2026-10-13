import { useEffect, useState } from 'react'

/**
 * Timestamp "sekarang" yang di-refresh berkala (default tiap menit) —
 * untuk bandingkan tenggat (`due_at`) tanpa memanggil `Date.now()`
 * saat render (dilarang react-hooks/purity).
 */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])

  return now
}
