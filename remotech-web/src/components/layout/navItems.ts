/** Konfigurasi menu navigasi, dipakai Navbar (desktop) dan MobileNav (drawer). */

export interface NavItem {
  key: string
  label: string
  to: string
  /** Hanya tampil bila user sudah login dan berrole mentor. */
  requiresMentor?: boolean
}

/** Menu tengah navbar — Kursus, plus Mentor untuk user mentor. */
export const primaryNavItems: NavItem[] = [
  { key: 'courses', label: 'Courses', to: '/courses' },
  { key: 'mentor', label: 'Mentor', to: '/mentor', requiresMentor: true },
]

/**
 * Filter menu utama sesuai status login & role.
 * Item `requiresMentor` hanya lolos bila login sekaligus mentor.
 */
export function getPrimaryNavItems(isAuthenticated: boolean, isMentor: boolean): NavItem[] {
  return primaryNavItems.filter((item) => !item.requiresMentor || (isAuthenticated && isMentor))
}

/** Menu akun di dropdown "Hi,{user}" dan drawer mobile. */
export const accountNavItems: NavItem[] = [
  { key: 'my-courses', label: 'Enrolled Course', to: '/my-courses' },
  { key: 'my-assignments', label: 'My Assignment', to: '/my-assignments' },
  { key: 'my-points', label: 'My Point', to: '/my-points' },
  { key: 'my-orders', label: 'My Order', to: '/my-orders' },
  { key: 'profile', label: 'Profile', to: '/profile' },
]
