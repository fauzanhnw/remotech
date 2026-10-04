import { usePageTitle } from '@/hooks/usePageTitle'

interface PlaceholderPageProps {
  title: string
  description?: string
}

/** Halaman sementara — isi sesungguhnya menyusul di task integrasi data. */
export function PlaceholderPage({
  title,
  description = 'This page is still under construction.',
}: PlaceholderPageProps) {
  usePageTitle(title)

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-semibold text-gray-900">{title}</h1>
      <p className="mt-2 text-gray-600">{description}</p>
    </section>
  )
}
