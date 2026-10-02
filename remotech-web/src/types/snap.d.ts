/**
 * Global `window.snap` dari script Snap Midtrans.
 * Script di-inject oleh `loadSnapScript()` di `@/api/services/snap`.
 */

/** Data yang dikembalikan Snap pada callback onSuccess/onPending/onError. */
interface SnapCallbackResult {
  status_code?: string
  status_message?: string
  order_id?: string
  transaction_id?: string
  transaction_status?: string
  payment_type?: string
}

interface SnapOptions {
  onSuccess?: (result: SnapCallbackResult) => void
  onPending?: (result: SnapCallbackResult) => void
  onError?: (result: SnapCallbackResult) => void
  onClose?: () => void
}

interface Window {
  snap?: {
    pay: (token: string, options?: SnapOptions) => void
  }
}
