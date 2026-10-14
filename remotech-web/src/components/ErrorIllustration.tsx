interface ErrorIllustrationProps {
  code: '404' | '403'
}

/** Ilustrasi kecil untuk halaman error — kode error digambar di bawah badan halaman. */
export function ErrorIllustration({ code }: ErrorIllustrationProps) {
  return (
    <svg
      viewBox="0 0 160 160"
      role="img"
      aria-label={`Error illustration ${code}`}
      className="mx-auto mt-6 h-32 w-32"
    >
      <circle cx="80" cy="80" r="76" fill="#eaf2ff" />
      <circle cx="130" cy="34" r="12" fill="#d9e7ff" />
      <circle cx="30" cy="128" r="9" fill="#d9e7ff" />

      {/* Lembar dokumen */}
      <path
        d="M52 28h44l20 20v84a8 8 0 0 1-8 8H52a8 8 0 0 1-8-8V36a8 8 0 0 1 8-8z"
        fill="#fff"
        stroke="#d7e4fb"
        strokeWidth="3"
      />
      <path d="M96 28l20 20H100a4 4 0 0 1-4-4V28z" fill="#d9e7ff" />
      <rect x="60" y="112" width="48" height="7" rx="3.5" fill="#eef3fb" />
      <rect x="60" y="124" width="34" height="7" rx="3.5" fill="#eef3fb" />

      {code === '404' ? (
        <>
          <circle cx="80" cy="74" r="22" fill="#1677ff" />
          <text
            x="80"
            y="83"
            textAnchor="middle"
            fill="#fff"
            fontSize="30"
            fontWeight="700"
            fontFamily="inherit"
          >
            ?
          </text>
        </>
      ) : (
        <>
          <path
            d="M70 78v-8a10 10 0 0 1 20 0v8"
            fill="none"
            stroke="#1677ff"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <rect x="62" y="76" width="36" height="28" rx="6" fill="#1677ff" />
          <circle cx="80" cy="88" r="4" fill="#fff" />
          <rect x="78.5" y="90" width="3" height="7" rx="1.5" fill="#fff" />
        </>
      )}
    </svg>
  )
}
