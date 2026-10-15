/**
 * Util preview konten video.
 * Backend membuang tag <iframe> yang src-nya bukan host embed yang diizinkan
 * (EMBED_HOSTS di richtext.py), sehingga embed YouTube/Google Drive dibangun
 * di sisi FE.
 */

const YOUTUBE_ID =
  /(?:youtube\.com\/(?:watch\?(?:[^#]*&)?v=|shorts\/|embed\/|live\/)|youtu\.be\/)([\w-]{11})/

const DRIVE_FILE_ID = /drive\.google\.com\/file\/d\/([\w-]{20,})/
const DRIVE_QUERY_ID = /drive\.google\.com\/(?:open|uc)\?(?:[^#]*&)?id=([\w-]{20,})/
const GOOGLE_DOC = /docs\.google\.com\/(?:document|presentation|spreadsheets)\/d\/([\w-]{20,})/

/** Ubah URL YouTube apa pun menjadi URL embed `youtube-nocookie`; null bila bukan YouTube. */
function toYouTubeEmbed(url: string): string | null {
  const match = url.match(YOUTUBE_ID)
  return match ? `https://www.youtube-nocookie.com/embed/${match[1]}` : null
}

/** Ubah URL share Google Drive / Google Docs menjadi URL `/preview` yang bisa di-embed. */
function toGoogleEmbed(url: string): string | null {
  const file = url.match(DRIVE_FILE_ID)
  if (file) return `https://drive.google.com/file/d/${file[1]}/preview`

  const query = url.match(DRIVE_QUERY_ID)
  if (query) return `https://drive.google.com/file/d/${query[1]}/preview`

  const doc = url.match(GOOGLE_DOC)
  if (doc) return `https://docs.google.com/${doc[0].split("/")[1]}/d/${doc[1]}/preview`

  return null
}

/**
 * Ubah URL video yang dikenal menjadi URL embed yang bisa dipasang di <iframe>;
 * null bila host tidak didukung. Mendukung YouTube dan Google Drive/Docs.
 */
export function toEmbedUrl(url: string): string | null {
  return toYouTubeEmbed(url) ?? toGoogleEmbed(url)
}

/** true bila URL mengarah ke file video langsung (mp4/webm/ogg). */
export function isDirectVideo(url: string): boolean {
  return /\.(mp4|webm|ogg)(\?.*)?$/i.test(url)
}
