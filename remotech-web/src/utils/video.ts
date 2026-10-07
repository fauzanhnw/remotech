/**
 * Util preview konten video.
 * Backend membuang tag <iframe> saat sanitasi richtext, sehingga embed
 * YouTube harus dibangun di sisi FE.
 */

const YOUTUBE_ID =
  /(?:youtube\.com\/(?:watch\?(?:[^#]*&)?v=|shorts\/|embed\/|live\/)|youtu\.be\/)([\w-]{11})/

/** Ubah URL YouTube apa pun menjadi URL embed `youtube-nocookie`; null bila bukan YouTube. */
export function toEmbedUrl(url: string): string | null {
  const match = url.match(YOUTUBE_ID)
  return match ? `https://www.youtube-nocookie.com/embed/${match[1]}` : null
}

/** true bila URL mengarah ke file video langsung (mp4/webm/ogg). */
export function isDirectVideo(url: string): boolean {
  return /\.(mp4|webm|ogg)(\?.*)?$/i.test(url)
}
