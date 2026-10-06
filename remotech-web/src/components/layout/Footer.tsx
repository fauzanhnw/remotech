import { MailOutlined } from '@ant-design/icons'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

interface FooterLink {
  key: string
  label: string
  to: string
}

interface FooterContact {
  key: string
  icon: ReactNode
  label: string
  href: string
}

/** Daftar kontak resmi — tambah entri baru di sini agar otomatis tampil di footer. */
const FOOTER_CONTACTS: FooterContact[] = [
  {
    key: 'email',
    icon: <MailOutlined />,
    label: 'admin@remotech.web.id',
    href: 'mailto:admin@remotech.web.id',
  },
]

const FOOTER_NAV: FooterLink[] = [
  { key: 'home', label: 'Home', to: '/' },
  { key: 'courses', label: 'Courses', to: '/courses' },
]

/** Footer gelap tiga kolom (brand, navigasi, kontak) + baris hak cipta. */
export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-[#08060d] text-sm text-gray-400">
      <div className="mx-auto max-w-7xl px-4 py-10 md:px-10">
        <div className="grid gap-8 text-center md:grid-cols-3 md:text-left">
          <div>
            <p className="text-lg font-bold text-white">Remotech</p>
            <p className="mt-2 leading-relaxed text-gray-500">
              Remote Challenge
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Navigasi
            </p>
            <ul className="mt-3 list-none space-y-2 p-0">
              {FOOTER_NAV.map((item) => (
                <li key={item.key}>
                  <Link
                    to={item.to}
                    className="text-gray-400 no-underline transition-colors hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              Kontak
            </p>
            <ul className="mt-3 list-none space-y-2 p-0">
              {FOOTER_CONTACTS.map((contact) => (
                <li
                  key={contact.key}
                  className="flex items-center justify-center gap-2 md:justify-start"
                >
                  <span className="text-gray-500">{contact.icon}</span>
                  <a
                    href={contact.href}
                    className="text-gray-400 no-underline transition-colors hover:text-white"
                    rel="noopener noreferrer"
                  >
                    {contact.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="mx-auto max-w-7xl px-4 py-4 text-center text-xs text-gray-500 md:px-10">
          © {new Date().getFullYear()} Remotech | Remote Circle Community
        </div>
      </div>
    </footer>
  )
}
