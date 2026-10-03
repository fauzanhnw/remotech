import { Button, Space } from 'antd'
import { useNavigate } from 'react-router-dom'

/** Tombol auth untuk tamu: Register (outline hitam) dan Login (outline primary). */
export function AuthButtons() {
  const navigate = useNavigate()

  return (
    <Space size={8}>
      <Button
        onClick={() => navigate('/register')}
        className="!font-medium !text-gray-900"
        style={{ borderColor: '#08060d' }}
      >
        Register
      </Button>
      <Button type="primary" ghost onClick={() => navigate('/login')}>
        Login
      </Button>
    </Space>
  )
}
