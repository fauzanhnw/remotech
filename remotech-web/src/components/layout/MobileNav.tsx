import { LogoutOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { accountNavItems, primaryNavItems } from './navItems'

interface MobileNavProps {
  open: boolean
  onClose: () => void
}

/** Panel menu yang meluas ke bawah navbar pada layar kecil (toggle lewat hamburger). */
export function MobileNav({ open, onClose }: MobileNavProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuth()

  const allItems = isAuthenticated ? [...primaryNavItems, ...accountNavItems] : primaryNavItems
  const selected = allItems.find((item) => location.pathname.startsWith(item.to))?.key

  if (!open) return null

  return (
    <div className="border-t border-gray-200 bg-white md:hidden">
      <nav className="flex flex-col gap-2 px-3 py-3">
        {allItems.map((item) => (
          <Link
            key={item.key}
            to={item.to}
            onClick={onClose}
            className={`block rounded-md px-3 py-2.5 text-center text-sm font-bold no-underline transition-colors ${
              selected === item.key ? 'bg-blue-50 text-[#1677ff]' : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-3 border-t border-gray-200 p-4">
        {isAuthenticated ? (
          <>
            <div>
              <p className="truncate text-center font-medium text-gray-900">
                {user?.full_name ?? 'Remotech User'}
              </p>
              <p className="truncate text-center text-xs text-gray-500">{user?.email ?? '—'}</p>
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
          </>
        ) : (
          <>
            <Button
              block
              className="auth-btn-dark font-medium"
              style={{ borderColor: '#08060d' }}
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
              className="auth-btn-primary"
              onClick={() => {
                onClose()
                navigate('/login')
              }}
            >
              Login
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
