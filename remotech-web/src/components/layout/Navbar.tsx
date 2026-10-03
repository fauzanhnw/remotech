import { MenuOutlined } from '@ant-design/icons'
import { Button, Image, Menu } from 'antd'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import logo from '@/assets/logo.webp'
import { useAuth } from '@/auth/AuthContext'
import { AuthButtons } from './AuthButtons'
import { MobileNav } from './MobileNav'
import { UserMenu } from './UserMenu'
import { primaryNavItems } from './navItems'

/** Navbar tiga bagian: logo (kiri), menu halaman (tengah), aksi auth (kanan). */
export function Navbar() {
  const location = useLocation()
  const { isAuthenticated } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const selected = primaryNavItems.find((item) => location.pathname.startsWith(item.to))?.key

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4">
        <Link to="/" className="flex shrink-0 items-center gap-2">
          <Image src={logo} alt="Logo" height={32} preview={false} />
        </Link>

        <div className="hidden flex-1 justify-center md:flex">
          <Menu
            mode="horizontal"
            className="min-w-0 border-none bg-transparent"
            style={{ boxShadow: 'none' }}
            selectedKeys={selected ? [selected] : []}
            items={primaryNavItems.map((item) => ({
              key: item.key,
              label: <Link to={item.to}>{item.label}</Link>,
            }))}
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
          {isAuthenticated ? <UserMenu /> : <AuthButtons />}
          <div className="md:hidden">
            <Button
              type="text"
              aria-label="Open navigation menu"
              icon={<MenuOutlined />}
              onClick={() => setDrawerOpen(true)}
            />
          </div>
        </div>
      </div>

      <MobileNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </header>
  )
}
