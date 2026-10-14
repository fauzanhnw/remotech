import { Link } from 'react-router-dom'

import { ErrorIllustration } from '@/components/ErrorIllustration'
import { usePageTitle } from '@/hooks/usePageTitle'

/** Halaman 403 — ditampilkan saat user login tapi tidak punya akses ke rute. */
export function ForbiddenPage() {
  usePageTitle('403 Forbidden')

  return (
    <section className="mx-auto max-w-5xl px-4 py-16 text-center">
      <h1 className="text-5xl font-semibold text-gray-900">403</h1>
      <ErrorIllustration code="403" />
      <p className="mt-4 text-gray-600">You don't have access to this page.</p>
      <Link
        to="/"
        className="mt-6 inline-block font-medium text-[#1677ff] hover:text-[#0958d9]"
      >
        Back to home page
      </Link>
    </section>
  )
}
