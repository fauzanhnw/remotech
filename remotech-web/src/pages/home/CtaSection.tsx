import { Button } from 'antd'
import { useNavigate } from 'react-router-dom'

import { cta } from './data'

/** Panel penutup gelap dengan CTA pendaftaran. */
export function CtaSection() {
  const navigate = useNavigate()

  return (
    <section id="cta" className="bg-[#08060d]">
      <div className="mx-auto max-w-4xl px-4 py-16 text-center md:py-20">
        <h2 className="text-3xl font-bold text-white md:text-4xl">{cta.title}</h2>
        <p className="mt-3 text-gray-400">{cta.description}</p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Button
            type="primary"
            size="large"
            className="font-medium"
            onClick={() => navigate('/register')}
          >
            {cta.primaryLabel}
          </Button>
          <Button
            ghost
            size="large"
            style={{ borderColor: '#3f3f46', color: '#fff' }}
            onClick={() => navigate('/courses')}
          >
            {cta.secondaryLabel}
          </Button>
        </div>
      </div>
    </section>
  )
}
