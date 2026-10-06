import { usePageTitle } from '@/hooks/usePageTitle'
import { CtaSection } from './home/CtaSection'
import { FaqSection } from './home/FaqSection'
import { FeaturesSection } from './home/FeaturesSection'
import { HeroSection } from './home/HeroSection'
import { StatsSection } from './home/StatsSection'

export function HomePage() {
  usePageTitle('Home')

  return (
    <>
      <HeroSection />
      <StatsSection />
      <FeaturesSection />
      <FaqSection />
      <CtaSection />
    </>
  )
}
