const rupiah = new Intl.NumberFormat('id-ID', {
  style: 'currency',
  currency: 'IDR',
  minimumFractionDigits: 0,
})

/** Format harga course: `0` → "Gratis", selain itu → "Rp150.000". */
export function formatRupiah(price: number): string {
  if (price <= 0) return 'Free'
  return rupiah.format(price)
}
