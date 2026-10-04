import { ConfigProvider } from 'antd'
import { BrowserRouter } from 'react-router-dom'

import { AuthProvider } from '@/auth/AuthProvider'
import { AppRoutes } from '@/routes'

export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: { colorPrimary: '#1677ff' },
        // Tanpa ink bar (garis bawah) pada item menu terpilih.
        components: { Menu: { activeBarHeight: 0 } },
      }}
    >
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  )
}
