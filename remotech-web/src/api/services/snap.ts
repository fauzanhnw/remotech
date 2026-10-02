/**
 * Integrasi Snap Midtrans (popup pembayaran).
 *
 * Alur: `enrollCourse()` → `payWithSnap(snap_token)` → `checkPayment(order.id)`.
 */

const SCRIPT_ID = 'midtrans-snap-script'
const SANDBOX_SCRIPT_URL = 'https://app.sandbox.midtrans.com/snap/snap.js'
const PRODUCTION_SCRIPT_URL = 'https://app.midtrans.com/snap/snap.js'

export type SnapResultStatus = 'success' | 'pending' | 'error' | 'closed'

export interface SnapResult {
  /**
   * - `success`/`pending`/`error`: callback dari Snap — `transactionStatus`
   *   berisi status dari Midtrans.
   * - `closed`: user menutup popup tanpa callback — tetap panggil
   *   `checkPayment()` untuk memastikan (kemungkinan besar masih pending).
   */
  status: SnapResultStatus
  orderId?: string
  transactionStatus?: string
  paymentType?: string
}

function requireClientKey(): string {
  const key = import.meta.env.VITE_MIDTRANS_CLIENT_KEY
  if (!key) {
    throw new Error('VITE_MIDTRANS_CLIENT_KEY belum di-set di .env')
  }
  return key
}

function scriptUrl(): string {
  return (
    import.meta.env.VITE_MIDTRANS_SNAP_URL ||
    (import.meta.env.PROD ? PRODUCTION_SCRIPT_URL : SANDBOX_SCRIPT_URL)
  )
}

let scriptPromise: Promise<void> | null = null

/** Inject script Snap sekali per halaman (idempoten). */
export function loadSnapScript(): Promise<void> {
  const snap = window.snap
  if (snap) return Promise.resolve()
  if (scriptPromise) return scriptPromise

  const clientKey = requireClientKey()
  scriptPromise = new Promise<void>((resolve, reject) => {
    const fail = () => {
      scriptPromise = null
      reject(new Error('Gagal memuat script Snap Midtrans.'))
    }

    const existing = document.getElementById(SCRIPT_ID)
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', fail, { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = SCRIPT_ID
    script.src = scriptUrl()
    script.async = true
    script.setAttribute('data-client-key', clientKey)
    script.addEventListener('load', () => resolve(), { once: true })
    script.addEventListener('error', fail, { once: true })
    document.body.appendChild(script)
  })

  return scriptPromise
}

function toResult(
  status: SnapResultStatus,
  payload: SnapCallbackResult,
): SnapResult {
  return {
    status,
    orderId: payload.order_id,
    transactionStatus: payload.transaction_status,
    paymentType: payload.payment_type,
  }
}

/**
 * Buka popup pembayaran Snap untuk satu token.
 *
 * Selalu resolve (tidak pernah reject akibat callback Snap): caller wajib
 * menindak setiap `status`, termasuk `closed`, dengan `checkPayment()`.
 */
export async function payWithSnap(token: string): Promise<SnapResult> {
  requireClientKey()
  await loadSnapScript()

  const snap = window.snap
  if (!snap) {
    throw new Error('Snap Midtrans tidak tersedia.')
  }

  return new Promise<SnapResult>((resolve) => {
    snap.pay(token, {
      onSuccess: (payload) => resolve(toResult('success', payload)),
      onPending: (payload) => resolve(toResult('pending', payload)),
      onError: (payload) => resolve(toResult('error', payload)),
      onClose: () => resolve({ status: 'closed' }),
    })
  })
}
