import logo from '@/assets/logo.webp'

/** Ilustrasi placeholder hero: susunan kartu UI abstrak dengan warna brand. */
export function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 480 480"
      role="img"
      aria-label="Ilustrasi dasbor Remote Challenge"
      className="h-auto w-full"
    >
      <rect width="480" height="480" rx="28" fill="#eaf2ff" />
      <circle cx="410" cy="80" r="64" fill="#d9e7ff" />
      <circle cx="64" cy="420" r="48" fill="#d9e7ff" />

      {/* Kartu modul */}
      <rect x="44" y="64" width="272" height="158" rx="18" fill="#fff" stroke="#d7e4fb" />
      <rect x="66" y="86" width="34" height="34" rx="10" fill="#e8f1ff" />
      <image href={logo} x="71" y="91" width="24" height="24" preserveAspectRatio="xMidYMid meet" />
      <rect x="112" y="94" width="128" height="12" rx="6" fill="#08060d" />
      <rect x="112" y="112" width="84" height="8" rx="4" fill="#c9d6ea" />
      <rect x="66" y="142" width="228" height="14" rx="7" fill="#eef3fb" />
      <rect x="66" y="142" width="146" height="14" rx="7" fill="#1677ff" />
      <rect x="66" y="170" width="180" height="9" rx="4.5" fill="#eef3fb" />
      <rect x="66" y="188" width="136" height="9" rx="4.5" fill="#eef3fb" />

      {/* Kartu poin */}
      <rect x="56" y="252" width="140" height="132" rx="18" fill="#08060d" />
      <circle cx="126" cy="298" r="26" fill="none" stroke="#2f2f3a" strokeWidth="8" />
      <path
        d="M126 272a26 26 0 0 1 22 40"
        fill="none"
        stroke="#1677ff"
        strokeWidth="8"
        strokeLinecap="round"
      />
      <rect x="86" y="336" width="80" height="14" rx="7" fill="#fff" />
      <rect x="96" y="358" width="60" height="9" rx="4.5" fill="#4b4b57" />

      {/* Kartu leaderboard */}
      <rect x="216" y="232" width="220" height="184" rx="18" fill="#fff" stroke="#d7e4fb" />
      <rect x="238" y="254" width="96" height="12" rx="6" fill="#08060d" />
      <g>
        <circle cx="252" cy="294" r="12" fill="#1677ff" />
        <rect x="274" y="288" width="94" height="12" rx="6" fill="#eef3fb" />
        <rect x="378" y="288" width="36" height="12" rx="6" fill="#1677ff" />
      </g>
      <g>
        <circle cx="252" cy="332" r="12" fill="#8fb6f5" />
        <rect x="274" y="326" width="76" height="12" rx="6" fill="#eef3fb" />
        <rect x="360" y="326" width="36" height="12" rx="6" fill="#c9d6ea" />
      </g>
      <g>
        <circle cx="252" cy="370" r="12" fill="#c9d6ea" />
        <rect x="274" y="364" width="64" height="12" rx="6" fill="#eef3fb" />
        <rect x="348" y="364" width="36" height="12" rx="6" fill="#c9d6ea" />
      </g>
    </svg>
  )
}
