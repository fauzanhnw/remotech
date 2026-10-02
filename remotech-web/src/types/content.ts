/**
 * Turunan course module: isi konten dan assignment.
 */

import type { IsoDateTime } from './common'

/** GET /module-content/{id}/ — `content_text` berisi HTML bersih dengan URL absolut. */
export interface ModuleContent {
  id: number
  module: number
  content_text: string
  content_url: string
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/**
 * POST /module-content/ — validasi bergantung kategori module:
 * `content_text` wajib untuk "text", `content_url` wajib untuk "video"/"upload".
 */
export interface ModuleContentCreate {
  module: number
  content_text?: string
  content_url?: string
}

/** GET /assignment/{id}/ */
export interface Assignment {
  id: number
  course_module: number
  name: string
  description: string
  created_at: IsoDateTime
  modified_at: IsoDateTime
}

/** POST /assignment/ — backend tidak auto-inject user. */
export interface AssignmentCreate {
  course_module: number
  name: string
  description: string
}
