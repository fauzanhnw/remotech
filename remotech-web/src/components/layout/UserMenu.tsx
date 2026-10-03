import {
  DownOutlined,
  FileTextOutlined,
  LogoutOutlined,
  ProfileOutlined,
  ShoppingCartOutlined,
  TrophyOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Button, Dropdown, type MenuProps } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '@/auth/AuthContext'
import { accountNavItems } from './navItems'

const iconByKey: Record<string, ReactNode> = {
  'my-courses': <ProfileOutlined />,
  'my-assignments': <FileTextOutlined />,
  'my-points': <TrophyOutlined />,
  'my-orders': <ShoppingCartOutlined />,
  profile: <UserOutlined />,
}

/** Dropdown akun "Hi,{user}" — hanya tampil saat sudah login. */
export function UserMenu() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const firstName = user?.first_name || user?.full_name.split(' ')[0] || 'Pengguna'

  const items: MenuProps['items'] = [
    ...accountNavItems.map((item) => ({
      key: item.to,
      icon: iconByKey[item.key],
      label: item.label,
    })),
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Logout' },
  ]

  const onItemClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      logout()
      navigate('/login')
      return
    }
    navigate(key)
  }

  return (
    <Dropdown
      trigger={['click']}
      overlayClassName="user-menu-popup"
      menu={{ items, onClick: onItemClick }}
      dropdownRender={(menu) => (
        <div className="min-w-56 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
          <div className="border-b border-gray-100 px-4 py-3">
            <p className="truncate font-medium text-gray-900">{user?.full_name ?? firstName}</p>
            <p className="truncate text-xs text-gray-500">{user?.email ?? '—'}</p>
          </div>
          {menu}
        </div>
      )}
    >
      <Button type="primary" icon={<DownOutlined />} iconPosition="end">
        Hi, {firstName}
      </Button>
    </Dropdown>
  )
}
