import { ConfigProvider } from 'antd'
import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/auth/AuthProvider'
import { AppRoutes } from '@/routes'

export default function App() {
  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#1677ff' } }}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  )
}
