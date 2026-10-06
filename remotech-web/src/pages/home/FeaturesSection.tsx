import { BookOutlined, CheckSquareOutlined, TrophyOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { features } from './data'

const featureIcons: Record<string, ReactNode> = {
  modules: <BookOutlined />,
  assignments: <CheckSquareOutlined />,
  gamification: <TrophyOutlined />,
}

/** Section abu-abu: argumen program di kiri, tiga kartu fitur di kanan. */
export function FeaturesSection() {
  const navigate = useNavigate()

  return (
    <section id="features" className="bg-gray-100">
      <div className="mx-auto max-w-7xl px-4 py-16 md:py-10">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div className="max-w-lg">
            <p className="text-xs font-semibold tracking-[0.2em] text-[#1677ff]">
              {features.eyebrow}
            </p>
            <h2 className="mt-4 text-3xl font-bold leading-tight text-[#08060d] md:text-4xl">
              {features.title}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-gray-600">{features.description}</p>
            <Button
              className="auth-btn-dark mt-6 font-medium"
              style={{ borderColor: '#08060d' }}
              onClick={() => navigate('/courses')}
            >
              {features.linkLabel}
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {features.cards.map((card) => (
              <div
                key={card.title}
                className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e8f1ff] text-xl text-[#1677ff]">
                  {featureIcons[card.icon]}
                </div>
                <h3 className="mt-4 font-semibold text-[#08060d]">{card.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{card.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
