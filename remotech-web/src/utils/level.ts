/**
 * Level on-the-fly dari total poin — pasangan frontend dari
 * `server.apps.remotech.services.levels`. Backend yang menghitung;
 * util ini hanya untuk warna/penomoran konsisten di UI.
 */

export const LEVEL_TITLES = [
  'Pemula',
  'Pelajar',
  'Praktisi',
  'Profesional',
  'Ahli',
  'Master',
] as const

/** Warna antd Tag per level (index = level - 1). */
const LEVEL_COLORS = ['default', 'blue', 'cyan', 'geekblue', 'purple', 'gold'] as const

export function levelColor(level: number): string {
  return LEVEL_COLORS[Math.min(Math.max(level, 1), 6) - 1]
}

/** Teks tag level, mis. "Lv.3 Praktisi". */
export function levelLabel(level: number, levelTitle: string): string {
  return `Lv.${level} ${levelTitle}`
}
