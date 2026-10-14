import { stats, statsSources } from './data'

/** Strip statistik tren kerja remote sebagai argumen "kenapa sekarang". */
export function StatsSection() {
  return (
    <section id="stats" className="border-y border-gray-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-10 md:py-12">
        <div className="grid gap-8 text-center sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.value}>
              <p className="text-4xl font-bold text-[#1677ff] md:text-5xl">{stat.value}</p>
              <p className="mt-2 text-sm text-gray-600 md:text-base">{stat.label}</p>
            </div>
          ))}
        </div>
        <p className="mt-8 text-center text-xs text-gray-400">
          Sumber:{' '}
          {statsSources.map((source, i) => (
            <span key={source.url}>
              {i > 0 && ' · '}
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="underline hover:text-gray-600"
              >
                {source.label}
              </a>
            </span>
          ))}
        </p>
      </div>
    </section>
  )
}
