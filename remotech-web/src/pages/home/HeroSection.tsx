import { Button } from 'antd'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'
import { hero } from './data'
import { HeroIllustration } from './HeroIllustration'

/** Section pembuka: judul, subjudul, CTA "Start Now", dan ilustrasi. */
export function HeroSection() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  return (
    <section id="hero" className="mx-auto max-w-7xl px-5 py-14 md:py-10 md:px-10">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div className="max-w-xl">
          <p className="text-xs font-semibold tracking-[0.2em] text-[#1677ff]">{hero.eyebrow}</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-[#08060d] md:text-5xl">
            {hero.title}
          </h1>
          <p className="mt-5 text-base leading-relaxed text-gray-600 md:text-lg">{hero.subtitle}</p>
          <p className="mt-3 text-base font-medium text-gray-500">{hero.tagline}</p>
          <Button
            type="primary"
            ghost
            size="large"
            className="auth-btn-primary mt-8 font-medium"
            onClick={() => navigate(isAuthenticated ? '/courses' : '/register')}
          >
            {hero.ctaLabel}
          </Button>
        </div>

        <div className="mx-auto w-full max-w-md lg:max-w-none">
          <HeroIllustration />
        </div>
      </div>
    </section>
  )
}
