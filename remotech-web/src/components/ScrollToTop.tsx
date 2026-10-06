import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Kembalikan posisi scroll ke paling atas setiap pindah halaman. */
export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
