const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

const toNumberOrNull = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

export async function fetchRecentParking(window = '15m') {
  const url = `${API_BASE}/pwa/parking/recent?window=${encodeURIComponent(window)}`.replace('//pwa', '/pwa')
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`Parking request failed (${res.status})`)

  const data = await res.json()
  if (!Array.isArray(data)) return []

  return data
    .map((item) => ({
      ...item,
      lat: toNumberOrNull(item.lat),
      lng: toNumberOrNull(item.lng),
      available_spots: toNumberOrNull(item.available_spots),
      total_spots: toNumberOrNull(item.total_spots),
    }))
    .filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
}
