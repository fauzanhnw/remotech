/** Konfigurasi menu navigasi, dipakai Navbar (desktop) dan MobileNav (drawer). */

export interface NavItem {
  key: string
  label: string
  to: string
}

/** Menu tengah navbar — hanya Kursus dulu. */
export const primaryNavItems: NavItem[] = [
  { key: 'courses', label: 'Courses', to: '/courses' },
  // { key: 'faq', label: 'FAQ', to: '/courses' },
]

/** Menu akun di dropdown "Hi,{user}" dan drawer mobile. */
export const accountNavItems: NavItem[] = [
  { key: 'my-courses', label: 'Enrolled Course', to: '/my-courses' },
  { key: 'my-assignments', label: 'My Assignment', to: '/my-assignments' },
  { key: 'my-points', label: 'My Point', to: '/my-points' },
  { key: 'my-orders', label: 'My Order', to: '/my-orders' },
  { key: 'profile', label: 'Profile', to: '/profile' },
]
