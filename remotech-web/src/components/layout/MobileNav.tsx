import { LogoutOutlined } from '@ant-design/icons'
import { Button, Drawer, Menu, type MenuProps, Space } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { accountNavItems, primaryNavItems } from './navItems'

interface MobileNavProps {
  open: boolean
  onClose: () => void
}

/** Drawer navigasi untuk layar kecil (pengganti menu tengah navbar). */
export function MobileNav({ open, onClose }: MobileNavProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuth()

  const allItems = isAuthenticated ? [...primaryNavItems, ...accountNavItems] : primaryNavItems
  const selected = allItems.find((item) => location.pathname.startsWith(item.to))?.key

  const items: MenuProps['items'] = allItems.map((item) => ({
    key: item.key,
    label: item.label,
  }))

  const handleClick: MenuProps['onClick'] = ({ key }) => {
    const target = allItems.find((item) => item.key === key)
    if (target) navigate(target.to)
    onClose()
  }

  return (
    <Drawer title="Remotech" placement="left" width={280} open={open} onClose={onClose}>
      <Menu
        mode="inline"
        className="border-none"
        selectedKeys={selected ? [selected] : []}
        items={items}
        onClick={handleClick}
      />

      <div className="mt-6 border-t border-gray-200 pt-4">
        {isAuthenticated ? (
          <div className="space-y-3">
            <div>
              <p className="truncate font-medium text-gray-900">{user?.full_name ?? 'Pengguna'}</p>
              <p className="truncate text-xs text-gray-500">{user?.email ?? '—'}</p>
            </div>
            <Button
              block
              icon={<LogoutOutlined />}
              onClick={() => {
                logout()
                onClose()
                navigate('/login')
              }}
            >
              Logout
            </Button>
          </div>
        ) : (
          <Space direction="vertical" className="w-full" size={8}>
            <Button
              block
              style={{ borderColor: '#08060d' }}
              className="!font-medium !text-gray-900"
              onClick={() => {
                onClose()
                navigate('/register')
              }}
            >
              Register
            </Button>
            <Button
              block
              type="primary"
              ghost
              onClick={() => {
                onClose()
                navigate('/login')
              }}
            >
              Login
            </Button>
          </Space>
        )}
      </div>
    </Drawer>
  )
}
