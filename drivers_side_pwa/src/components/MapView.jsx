import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { fetchRecentTraffic } from '../services/traffic'
import { fetchRecentParking } from '../services/parking'

const cityCenter = [38.2464, 21.7346]
const beach = [38.2588, 21.7347]

function MapView({ active }) {
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const routeRef = useRef(null)
  const trafficLayerRef = useRef(null)
  const userMarkerRef = useRef(null)
  const parkingLayerRef = useRef(null)
  const nearestParkingMarkerRef = useRef(null)
  const [followUser, setFollowUser] = useState(true)
  const [hasCenteredInitially, setHasCenteredInitially] = useState(false)
  const [showCenterButton, setShowCenterButton] = useState(false)
  const latestUserLatLngRef = useRef(null)
  const suppressMoveEventRef = useRef(false)
  const followUserRef = useRef(true)
  const userInteractionTimerRef = useRef(null)
  const isUserInteractingRef = useRef(false)

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
    delete L.Icon.Default.prototype._getIconUrl
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
    
    // Create a custom pane for routes with lower z-index (below overlays but above tiles)
    map.createPane('routePane')
    map.getPane('routePane').style.zIndex = 350 // default overlayPane is 400
    
    setTimeout(() => map.invalidateSize(), 0)

    mapRef.current = map
    let cancelled = false
    let trafficIntervalId
    let geoWatchId
    const container = mapContainerRef.current
    const handleUserInteraction = () => {
      // Mark that user is actively interacting
      isUserInteractingRef.current = true
      followUserRef.current = false
      setFollowUser(false)
      setShowCenterButton(true)
      
      // Clear any existing timer
      if (userInteractionTimerRef.current) {
        clearTimeout(userInteractionTimerRef.current)
      }
      
      // Set timer to re-enable following only if user clicks center button explicitly
      userInteractionTimerRef.current = setTimeout(() => {
        isUserInteractingRef.current = false
      }, 5000) // 5 second grace period
      
      console.log("User interaction detected: Disabled following for 5 seconds")
    }

    if (container) {
      container.addEventListener('touchstart', handleUserInteraction, { passive: true })
      container.addEventListener('mousedown', handleUserInteraction)
      container.addEventListener('wheel', handleUserInteraction, { passive: true })
    }

    // If user manually moves the map, stop following and show the center button
    map.on('movestart', () => {
      // Ignore programmatic moves triggered by our own setView
      if (suppressMoveEventRef.current) {
        suppressMoveEventRef.current = false
        return
      }
      setFollowUser(false)
      setShowCenterButton(true)
    })

    // Additional listeners for immediate detection of user interactions on mobile
    map.on('dragstart', () => {
      setFollowUser(false)
      setShowCenterButton(true)
    })

    map.on('zoomstart', () => {
      setFollowUser(false)
      setShowCenterButton(true)
    })

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

    // Always show user's location using geolocation watch
    if (navigator.geolocation) {
      geoWatchId = navigator.geolocation.watchPosition(
        (pos) => {
          const latlng = [pos.coords.latitude, pos.coords.longitude]
          latestUserLatLngRef.current = latlng
          placeUserMarker(latlng)
          const m = mapRef.current
          if (!m) return
          
          // Don't move map if user is actively interacting
          if (isUserInteractingRef.current) {
            console.log("User interacting: Skipping GPS-based centering")
            return
          }
          
          if (!hasCenteredInitially) {
            // Center once by default on the first location fix, without showing the button yet
            suppressMoveEventRef.current = true
            m.setView(latlng, m.getZoom(), { animate: true })
            setHasCenteredInitially(true)
            // After initial center, stop following until the user asks
            followUserRef.current = false
            setFollowUser(false)
            setShowCenterButton(false)
          } else if (followUserRef.current) {
            // Only follow if ref is true AND user isn't interacting
            suppressMoveEventRef.current = true
            m.setView(latlng, m.getZoom(), { animate: false })
          } else {
            // Not following: just update the marker, don't move the map
            placeUserMarker(latlng)
          }
        },
        (err) => {
          console.error('Geolocation error', err)
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 10000 },
      )
    }

    return () => {
      cancelled = true
      if (trafficIntervalId) clearInterval(trafficIntervalId)
      if (userInteractionTimerRef.current) clearTimeout(userInteractionTimerRef.current)
      if (geoWatchId != null && navigator.geolocation) {
        navigator.geolocation.clearWatch(geoWatchId)
        geoWatchId = null
      }
      if (container) {
        container.removeEventListener('touchstart', handleUserInteraction)
        container.removeEventListener('mousedown', handleUserInteraction)
        container.removeEventListener('wheel', handleUserInteraction)
      }
      if (trafficLayerRef.current) {
        map.removeLayer(trafficLayerRef.current)
        trafficLayerRef.current = null
      }
      map.remove()
      mapRef.current = null
      routeRef.current = null
      userMarkerRef.current = null
      parkingLayerRef.current = null
      nearestParkingMarkerRef.current = null
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
      const poly = L.polyline(latlngs, { 
        color: '#4fd1c5', 
        weight: 5, 
        opacity: 0.9,
        pane: 'routePane'
      }).addTo(map)
      routeRef.current = poly
      map.fitBounds(poly.getBounds(), { padding: [30, 30] })
      // Ensure center button appears after route moves the map
      setShowCenterButton(true)
      followUserRef.current = false
      setFollowUser(false)
    } catch (err) {
      console.error(err)
    }
  }

  const placeUserMarker = (latlng) => {
    const map = mapRef.current
    if (!map) return
    if (userMarkerRef.current) {
      map.removeLayer(userMarkerRef.current)
      userMarkerRef.current = null
    }
    const marker = L.circleMarker(latlng, {
      radius: 7,
      color: '#0ea5e9',
      weight: 2,
      fillColor: '#38bdf8',
      fillOpacity: 1,
      title: 'Your location',
    }).addTo(map)
    userMarkerRef.current = marker
  }

  const placeNearestParkingMarker = (latlng, street = '') => {
    const map = mapRef.current
    if (!map) return
    if (nearestParkingMarkerRef.current) {
      map.removeLayer(nearestParkingMarkerRef.current)
      nearestParkingMarkerRef.current = null
    }
    const marker = L.marker(latlng, { title: street || 'Nearest parking' }).addTo(map)
    nearestParkingMarkerRef.current = marker
  }

  const centerOnUser = () => {
    const map = mapRef.current
    const latlng = latestUserLatLngRef.current
    if (!map || !latlng) return
    
    // Clear any pending interaction timer and reset interaction flag
    if (userInteractionTimerRef.current) {
      clearTimeout(userInteractionTimerRef.current)
    }
    isUserInteractingRef.current = false
    
    followUserRef.current = true
    setFollowUser(true)
    setShowCenterButton(false)
    suppressMoveEventRef.current = true
    map.setView(latlng, map.getZoom(), { animate: true })
  }

  const haversineDistanceKm = (a, b) => {
    const toRad = (d) => (d * Math.PI) / 180
    const R = 6371
    const dLat = toRad(b[0] - a[0])
    const dLng = toRad(b[1] - a[1])
    const lat1 = toRad(a[0])
    const lat2 = toRad(b[0])
    const h =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.sin(dLng / 2) * Math.sin(dLng / 2) * Math.cos(lat1) * Math.cos(lat2)
    return 2 * R * Math.asin(Math.sqrt(h))
  }

  const findNearestParking = async (fromLatLng) => {
    try {
      const parking = await fetchRecentParking()
      const candidates = parking.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lng))
      if (!candidates.length) return null

      const sorted = candidates
        .map((p) => ({
          ...p,
          distance: haversineDistanceKm(fromLatLng, [p.lat, p.lng]),
        }))
        .sort((a, b) => a.distance - b.distance)
      return sorted[0]
    } catch (err) {
      console.error('Failed to load parking data', err)
      return null
    }
  }

  const showParkingLayer = async () => {
    const map = mapRef.current
    if (!map) return
    try {
      const parking = await fetchRecentParking()
      if (parkingLayerRef.current) {
        map.removeLayer(parkingLayerRef.current)
        parkingLayerRef.current = null
      }
      if (!parking.length) return
      const layer = L.layerGroup(
        parking.map((p) => {
          const popup = `<strong>Parking</strong><br/>Street: ${p.street || 'n/a'}<br/>Available: ${p.available_spots ?? 'n/a'}/${p.total_spots ?? 'n/a'}`
          
          // If geometry is a LineString, render as a polyline
          if (p.geometry?.type === 'LineString' && p.geometry.coordinates?.length >= 2) {
            const coords = p.geometry.coordinates.map(([lng, lat]) => [lat, lng])
            return L.polyline(coords, {
              color: '#2563eb',
              weight: 4,
              opacity: 0.8,
            }).bindPopup(popup)
          }
          
          // Otherwise, render as a circle marker at centroid
          return L.circleMarker([p.lat, p.lng], {
            radius: 6,
            color: '#2563eb',
            weight: 2,
            fillColor: '#3b82f6',
            fillOpacity: 0.8,
          }).bindPopup(popup)
        }),
      ).addTo(map)
      parkingLayerRef.current = layer
    } catch (err) {
      console.error('Failed to render parking layer', err)
    }
  }

  // Render only a single selected parking zone
  const showSelectedParking = async (p) => {
    const map = mapRef.current
    if (!map || !p) return
    try {
      if (parkingLayerRef.current) {
        map.removeLayer(parkingLayerRef.current)
        parkingLayerRef.current = null
      }

      const popup = `<strong>Parking</strong><br/>Street: ${p.street || 'n/a'}<br/>Available: ${p.available_spots ?? 'n/a'}/${p.total_spots ?? 'n/a'}`

      let layer
      if (p.geometry?.type === 'LineString' && p.geometry.coordinates?.length >= 2) {
        const coords = p.geometry.coordinates.map(([lng, lat]) => [lat, lng])
        layer = L.layerGroup([
          L.polyline(coords, { color: '#2563eb', weight: 4, opacity: 0.9 }).bindPopup(popup),
        ]).addTo(map)
      } else {
        layer = L.layerGroup([
          L.circleMarker([p.lat, p.lng], { radius: 6, color: '#2563eb', weight: 2, fillColor: '#3b82f6', fillOpacity: 0.8 }).bindPopup(popup),
        ]).addTo(map)
      }
      parkingLayerRef.current = layer
    } catch (err) {
      console.error('Failed to render selected parking', err)
    }
  }

  const routeToNearestParking = async () => {
    if (!navigator.geolocation) {
      console.error('Geolocation not supported')
      return
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const from = [pos.coords.latitude, pos.coords.longitude]
        placeUserMarker(from)
        const nearest = await findNearestParking(from)
        if (!nearest) {
          console.error('No parking data available')
          return
        }
        const to = [nearest.lat, nearest.lng]
        // Destination parking entity is rendered as geometry; no extra marker
        await showSelectedParking(nearest)
        await makeRoute(from, to)
      },
      (err) => {
        console.error('Geolocation error', err)
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 },
    )
  }

  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="map-card">
      <article className="card map-card">
        <div className="body">
          <div id="map" ref={mapContainerRef}></div>
          <button className="map-fab" type="button" onClick={routeToNearestParking} aria-label="Route to nearest parking">
            P
          </button>
          {showCenterButton && latestUserLatLngRef.current && (
            <button
              className="map-fab"
              type="button"
              onClick={centerOnUser}
              aria-label="Center on my location"
              title="Center on my location"
              style={{ bottom: '72px' }}
            >
              ⊙
            </button>
          )}
        </div>
      </article>
    </section>
  )
}

export default MapView
