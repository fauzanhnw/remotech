/**
 * Course dan isinya yang berhubungan langsung: course → course module.
 * (ModuleContent & Assignment yang merupakan turunan module ada di content.ts)
 */

import type { IsoDateTime } from './common'

export type ModuleCategory = 'text' | 'video' | 'upload' | 'quiz'

/** GET /course/{id}/ — `user` & `slug` read-only, thumbnail URL absolut. */
export interface Course {
  id: number
  user: number
  /** Nama uploader: `get_full_name()` fallback ke username. */
  user_name: string
  slug: string
  title: string
  description: string
  thumbnail: string | null
  price: number
  is_publish: boolean
  /** false = course ditutup, pembelian baru tidak diterima. */
  is_open: boolean
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/** POST /course/ — `user` & `slug` di-auto-assign backend. */
export interface CourseCreate {
  title: string
  description?: string
  /** Kirim sebagai multipart/form-data (file image, otomatis dikonversi webp). */
  thumbnail?: File
  price?: number
  is_publish?: boolean
  /** Opsional — bila tidak dikirim, backend default `true` (buka). */
  is_open?: boolean
}

/**
 * PATCH /course/{id}/ — serupa `CourseCreate` dengan `thumbnail` opsional:
 * `File` mengganti gambar, `''` menghapus thumbnail, tidak dikirim = tetap.
 */
export interface CourseUpdate extends Omit<Partial<CourseCreate>, 'thumbnail'> {
  thumbnail?: File | ''
}

/** GET /module/{id}/ */
export interface CourseModule {
  id: number
  course: number
  title: string
  /** Deskripsi singkat module (kosong bila tidak diisi mentor). */
  description: string
  module_category: ModuleCategory
  sequence: number | null
  point: number
  /** Tenggat pengumpulan (kategori upload/quiz); null = tanpa tenggat. */
  due_at: IsoDateTime | null
  /** Persen poin yang dipotong bila submit melewati tenggat (0–100). */
  late_penalty_percent: number
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/** POST /module/ — `sequence` di-auto-assign, wajib pemilik course (403). */
export interface CourseModuleCreate {
  course: number
  title: string
  description?: string
  module_category?: ModuleCategory
  sequence?: number | null
  point?: number
  /** ISO datetime; hanya bermakna untuk kategori upload/quiz. */
  due_at?: string | null
  late_penalty_percent?: number
}
