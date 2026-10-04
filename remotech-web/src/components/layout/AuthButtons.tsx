import { Button, Space } from 'antd'
import { useNavigate } from 'react-router-dom'

/** Tombol auth untuk tamu: Register (outline hitam) dan Login (outline primary). */
export function AuthButtons() {
  const navigate = useNavigate()

  return (
    <Space size={8}>
      <Button
        onClick={() => navigate('/register')}
        className="auth-btn-dark font-medium"
        style={{ borderColor: '#08060d' }}
      >
        Register
      </Button>
      <Button type="primary" ghost className="auth-btn-primary" onClick={() => navigate('/login')}>
        Login
      </Button>
    </Space>
  )
}
