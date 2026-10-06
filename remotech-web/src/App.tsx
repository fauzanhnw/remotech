import { App as AntApp, ConfigProvider } from 'antd'
import { useEffect } from 'react'
import { BrowserRouter } from 'react-router-dom'

import { registerNotificationApi } from '@/api'
import { AuthProvider } from '@/auth/AuthProvider'
import { ScrollToTop } from '@/components/ScrollToTop'
import { AppRoutes } from '@/routes'

/** Pasang instance notification antd `<App>` agar `notify.*` berfungsi di luar komponen. */
function ToastBridge() {
  const { notification } = AntApp.useApp()
  useEffect(() => {
    registerNotificationApi(notification)
  }, [notification])
  return null
}

export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: { colorPrimary: '#1677ff' },
        // Tanpa ink bar (garis bawah) pada item menu terpilih.
        components: { Menu: { activeBarHeight: 0 } },
      }}
    >
      <AntApp notification={{ placement: 'bottomRight' }}>
        <AuthProvider>
          <BrowserRouter>
            <ScrollToTop />
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
        <ToastBridge />
      </AntApp>
    </ConfigProvider>
  )
}
