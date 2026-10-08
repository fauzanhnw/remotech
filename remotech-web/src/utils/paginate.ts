import type { Paginated, PaginationParams } from '@/types/api'

/** page_size maksimum yang diizinkan backend (`max_page_size`). */
export const MAX_PAGE_SIZE = 100

/**
 * Ambil semua halaman dari endpoint terpaginasi (DRF `PageNumberPagination`).
 *
 * Backend membatasi `page_size` maksimal 100, jadi daftar "semua data"
 * (mis. semua submission milik sendiri) harus di-loop sampai `next` habis.
 */
export async function fetchAllPages<T>(
  list: (params: PaginationParams) => Promise<Paginated<T>>,
): Promise<T[]> {
  const results: T[] = []
  let page = 1

  for (;;) {
    const chunk = await list({ page, page_size: MAX_PAGE_SIZE })
    results.push(...chunk.results)
    if (chunk.next == null || chunk.results.length === 0) return results
    page += 1
  }
}
