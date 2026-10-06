import { Link } from 'react-router-dom'

import { ErrorIllustration } from '@/components/ErrorIllustration'
import { usePageTitle } from '@/hooks/usePageTitle'

export function NotFoundPage() {
  usePageTitle('Page Not Found')

  return (
    <section className="mx-auto max-w-5xl px-4 py-16 text-center">
      <h1 className="text-5xl font-semibold text-gray-900">404</h1>
      <ErrorIllustration code="404" />
      <p className="mt-4 text-gray-600">The page you are looking for does not exist.</p>
      <Link
        to="/"
        className="mt-6 inline-block font-medium text-[#1677ff] hover:text-[#0958d9]"
      >
        Back to Home
      </Link>
    </section>
  )
}
