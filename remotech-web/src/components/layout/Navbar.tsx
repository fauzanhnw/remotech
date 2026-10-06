import { CloseOutlined, MenuOutlined } from '@ant-design/icons'
import { Button, Image, Menu } from 'antd'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import logo from '@/assets/logo.webp'
import { useAuth } from '@/auth/AuthContext'
import { AuthButtons } from './AuthButtons'
import { MobileNav } from './MobileNav'
import { UserMenu } from './UserMenu'
import { getPrimaryNavItems } from './navItems'

/** Navbar tiga bagian: logo (kiri), menu halaman (tengah), aksi auth (kanan). */
export function Navbar() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const navItems = getPrimaryNavItems(isAuthenticated, user?.is_mentor ?? false)
  const selected = navItems.find((item) => location.pathname.startsWith(item.to))?.key

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur shadow-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4">
        <Link to="/" className="flex shrink-0 items-center gap-2" onClick={() => setMenuOpen(false)}>
          <Image src={logo} alt="Logo" height={32} preview={false} />
        </Link>

        <div className="hidden flex-1 md:block border-r">
          <Menu
            mode="horizontal"
            className="border-none bg-transparent justify-end"
            style={{ boxShadow: 'none', borderBottom: 0 }}
            selectedKeys={selected ? [selected] : []}
            items={navItems.map((item) => ({
              key: item.key,
              label: (
                <Link to={item.to} className="font-bold no-underline">
                  {item.label}
                </Link>
              ),
            }))}
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
          <div className="hidden md:block">
            {isAuthenticated ? <UserMenu /> : <AuthButtons />}
          </div>
          <div className="md:hidden">
            <Button
              type="text"
              aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={menuOpen}
              icon={menuOpen ? <CloseOutlined /> : <MenuOutlined />}
              onClick={() => setMenuOpen((open) => !open)}
            />
          </div>
        </div>
      </div>

      <MobileNav open={menuOpen} onClose={() => setMenuOpen(false)} />
    </header>
  )
}
