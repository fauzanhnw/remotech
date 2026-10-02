/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** Public client key Midtrans (Snap). */
  readonly VITE_MIDTRANS_CLIENT_KEY: string
  /** Override URL script Snap; default mengikuti mode (dev=sandbox, prod=production). */
  readonly VITE_MIDTRANS_SNAP_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
