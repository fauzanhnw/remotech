import { MailOutlined } from '@ant-design/icons'
import type { ReactNode } from 'react'

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

/** Footer dua baris: kontak di atas (menumpuk vertikal), hak cipta di bawah. */
export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white">
      <div className="border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 py-5 text-center md:text-left md:px-10">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 pt-2">Kontak</p>
          <ul className="mt-2 space-y-2 text-sm">
            {FOOTER_CONTACTS.map((contact) => (
              <li
                key={contact.key}
                className="flex items-center justify-center gap-2 md:justify-start"
              >
                <span className="text-gray-400">{contact.icon}</span>
                <a
                  href={contact.href}
                  className="text-gray-600 no-underline hover:underline"
                  rel="noopener noreferrer"
                >
                  {contact.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-5 text-center text-sm text-gray-500">
        © {new Date().getFullYear()} Remotech | Remote Circle Community
      </div>
    </footer>
  )
}
