/** POST /content-view/{contentId}/ — hasil penandaan konten sudah dibuka. */
export interface ContentViewMarkResult {
  /** True bila penandaan ini menyelesaikan module (semua konten sudah dilihat). */
  module_completed: boolean
}

/** GET /content-view/?course= — id konten yang sudah dibuka (milik sendiri). */
export interface ContentViewedList {
  content_ids: number[]
}
