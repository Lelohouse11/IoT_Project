const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

const toNumberOrNull = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

const normalizeBool = (value) => {
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true' || value === '1'
  }
  return Boolean(value)
}

export async function fetchRecentTraffic(window = '15m') {
  const url = `${API_BASE}/pwa/traffic/recent?window=${encodeURIComponent(window)}`.replace('//pwa', '/pwa')
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`Traffic request failed (${res.status})`)

  const data = await res.json()
  if (!Array.isArray(data)) return []

  return data.map((item) => {
    const lat = toNumberOrNull(item.lat)
    const lng = toNumberOrNull(item.lng)
    return {
      ...item,
      lat,
      lng,
      intensity: toNumberOrNull(item.intensity),
      avg_speed: toNumberOrNull(item.avg_speed),
      density: toNumberOrNull(item.density),
      occupancy: toNumberOrNull(item.occupancy),
      congested: normalizeBool(item.congested),
      geometry: item.geometry ?? { type: 'Point', coordinates: [lng ?? 0, lat ?? 0] },
    }
  })
}
