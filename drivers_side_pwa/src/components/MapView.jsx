import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { fetchRecentTraffic } from '../api/traffic'

const cityCenter = [38.2464, 21.7346]
const beach = [38.2588, 21.7347]

function MapView({ active }) {
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const routeRef = useRef(null)
  const trafficLayerRef = useRef(null)

  const trafficColor = (props = {}) => {
    if (props.congested) return '#dc2626'
    const congestion = (props.congestion || '').toString().toLowerCase()
    if (congestion === 'high') return '#f97316'
    if (congestion === 'medium') return '#f59e0b'
    if (congestion === 'low') return '#22c55e'
    const speed = Number(props.avg_speed)
    if (Number.isFinite(speed)) {
      if (speed < 15) return '#dc2626'
      if (speed < 25) return '#f97316'
      if (speed < 40) return '#fbbf24'
    }
    return '#10b981'
  }

  // configure Leaflet default marker assets once
  useEffect(() => {
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: markerIcon2x,
      iconUrl: markerIcon,
      shadowUrl: markerShadow,
    })
  }, [])

  // initialize map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const map = L.map(mapContainerRef.current, { zoomControl: true, scrollWheelZoom: true }).setView(cityCenter, 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    setTimeout(() => map.invalidateSize(), 0)

    mapRef.current = map
    let cancelled = false
    let trafficIntervalId

    const renderTraffic = async () => {
      try {
        const traffic = await fetchRecentTraffic()
        if (cancelled) return

        const features = traffic.map((item) => ({
          type: 'Feature',
          geometry: item.geometry,
          properties: {
            id: item.id,
            congestion: item.congestion,
            congested: item.congested,
            avg_speed: item.avg_speed,
            intensity: item.intensity,
          },
        }))

        if (trafficLayerRef.current) {
          map.removeLayer(trafficLayerRef.current)
          trafficLayerRef.current = null
        }

        if (!features.length) return

        const layer = L.geoJSON(
          { type: 'FeatureCollection', features },
          {
            style: (feature) => ({
              color: trafficColor(feature.properties),
              weight: 6,
              opacity: 0.9,
            }),
            pointToLayer: (feature, latlng) => {
              const color = trafficColor(feature.properties)
              return L.circleMarker(latlng, {
                radius: 6,
                color,
                weight: 2,
                fillColor: color,
                fillOpacity: 0.8,
              })
            },
            onEachFeature: (feature, layer) => {
              const props = feature.properties || {}
              const speed = Number.isFinite(props.avg_speed) ? `${props.avg_speed.toFixed(1)} km/h` : 'n/a'
              const intensity = props.intensity ?? 'n/a'
              const congestion = props.congestion || (props.congested ? 'congested' : 'normal')
              layer.bindPopup(`<strong>Traffic</strong><br/>Speed: ${speed}<br/>Intensity: ${intensity}<br/>Congestion: ${congestion}`)
            },
          },
        ).addTo(map)
        trafficLayerRef.current = layer
      } catch (err) {
        if (!cancelled) console.error('Failed to load traffic data', err)
      }
    }

    renderTraffic()
    trafficIntervalId = window.setInterval(renderTraffic, 60000)

    return () => {
      cancelled = true
      if (trafficIntervalId) clearInterval(trafficIntervalId)
      if (trafficLayerRef.current) {
        map.removeLayer(trafficLayerRef.current)
        trafficLayerRef.current = null
      }
      map.remove()
      mapRef.current = null
      routeRef.current = null
    }
  }, [])

  // handle map resize on tab change
  useEffect(() => {
    if (active && mapRef.current) {
      setTimeout(() => mapRef.current?.invalidateSize(), 120)
    }
  }, [active])

  // create a route using GraphHopper API
  const makeRoute = async (start, end) => {
    const map = mapRef.current
    const key = import.meta.env.VITE_GRAPHHOPPER_KEY
    if (!map || !key) return

    try {
      if (routeRef.current) {
        map.removeLayer(routeRef.current)
        routeRef.current = null
      }

      const url = new URL('https://graphhopper.com/api/1/route')
      url.searchParams.set('point', `${start[0]},${start[1]}`)
      url.searchParams.append('point', `${end[0]},${end[1]}`)
      url.searchParams.set('vehicle', 'car')
      url.searchParams.set('locale', 'en')
      url.searchParams.set('points_encoded', 'false')
      url.searchParams.set('instructions', 'false')
      url.searchParams.set('key', key)

      const res = await fetch(url.toString(), { headers: { Accept: 'application/json' } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const coords = data?.paths?.[0]?.points?.coordinates
      if (!coords || !coords.length) throw new Error('Keine Route erhalten')

      const latlngs = coords.map(([lng, lat]) => [lat, lng])
      const poly = L.polyline(latlngs, { color: '#4fd1c5', weight: 5, opacity: 0.9 }).addTo(map)
      routeRef.current = poly
      map.fitBounds(poly.getBounds(), { padding: [30, 30] })
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="map-card">
      <article className="card map-card">
        <div className="body">
          <div id="map" ref={mapContainerRef}></div>
          <button className="map-fab" type="button" onClick={() => makeRoute(cityCenter, beach)} aria-label="Show route to parking">
            P
          </button>
        </div>
      </article>
    </section>
  )
}

export default MapView
