import { Outlet, useLocation } from 'react-router-dom'

import { Footer } from './Footer'
import { Navbar } from './Navbar'

/** Detail course enrolled (`/my-courses/{id}`) tampil full-bleed tanpa Navbar. */
const FULL_BLEED_PATTERN = /^\/my-courses\/[^/]+\/?$/

/** Kerangka halaman: Navbar + konten + Footer. */
export function AppShell() {
  const { pathname } = useLocation()
  const fullBleed = FULL_BLEED_PATTERN.test(pathname)

  return (
    <div className="flex min-h-svh flex-col bg-white">
      {!fullBleed && <Navbar />}
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
