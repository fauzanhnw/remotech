import { useEffect } from 'react'

const SUFFIX = 'Remotech'

/**
 * Set judul tab browser secara dinamis: `<title> | Remotech`.
 * Tanpa argumen (atau string kosong) judul kembali menjadi `Remotech`.
 */
export function usePageTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} | ${SUFFIX}` : SUFFIX
  }, [title])
}
