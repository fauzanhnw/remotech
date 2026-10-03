import { Image } from 'antd'
import type { ReactNode } from 'react'

import logo from '@/assets/logo.webp'

interface AuthCardProps {
  children: ReactNode
}

/** Kartu terpusat untuk halaman auth — logo di atas, lalu isi form. */
export function AuthCard({ children }: AuthCardProps) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-gray-50 px-4 py-10">
      <div className="w-full max-w-xl rounded-2xl border border-gray-200 bg-white p-8 shadow-sm md:p-10">
        <div className="mb-8 flex justify-center">
          <Image src={logo} alt="Remotech" width={220} preview={false} />
        </div>
        {children}
      </div>
    </div>
  )
}
