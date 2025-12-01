import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import './App.css'

const cityCenter = [38.2464, 21.7346]
const beach = [38.2588, 21.7347]
const evPoints = [
  [38.2488, 21.7301],
  [38.2441, 21.7398],
  [38.2532, 21.7443],
  [38.2505, 21.728],
]

function App() {
  const [profileOpen, setProfileOpen] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [activeTab, setActiveTab] = useState('map')
  const [points, setPoints] = useState(1250)
  const [reportType, setReportType] = useState('accident')
  const [reportMsg, setReportMsg] = useState('Help improve the map by reporting issues.')
  const [parkingMsg, setParkingMsg] = useState('')
  const [routeMsg, setRouteMsg] = useState('')

  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const routeRef = useRef(null)
  const evLayerRef = useRef(null)

  useEffect(() => {
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: markerIcon2x,
      iconUrl: markerIcon,
      shadowUrl: markerShadow,
    })

    const onClick = (e) => {
      if (profileOpen) {
        const menu = document.getElementById('profileMenu')
        const button = document.getElementById('profileBtn')
        if (menu && !menu.contains(e.target) && button && !button.contains(e.target)) {
          setProfileOpen(false)
        }
      }
    }
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setProfileOpen(false)
      }
    }
    document.addEventListener('click', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('click', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [profileOpen])

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    const map = L.map(mapContainerRef.current, { zoomControl: true, scrollWheelZoom: true }).setView(cityCenter, 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    setTimeout(() => map.invalidateSize(), 0)

    const evLayer = L.featureGroup()
    evPoints.forEach(([lat, lng]) =>
      L.circleMarker([lat, lng], { radius: 7, weight: 2, color: '#4fd1c5' })
        .bindTooltip('EV Charger')
        .addTo(evLayer)
    )

    mapRef.current = map
    evLayerRef.current = evLayer

    return () => {
      map.remove()
      mapRef.current = null
      evLayerRef.current = null
      routeRef.current = null
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'map' && mapRef.current) {
      setTimeout(() => mapRef.current?.invalidateSize(), 120)
    }
  }, [activeTab])

  const makeRoute = async (start, end) => {
    const map = mapRef.current
    const key = import.meta.env.VITE_GRAPHHOPPER_KEY
    if (!map) return
    if (!key) {
      setRouteMsg('Routing API-Key fehlt (VITE_GRAPHHOPPER_KEY).')
      return
    }

    try {
      setRouteMsg('Route wird geladen ...')
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
      setRouteMsg('Route geladen.')
    } catch (err) {
      console.error(err)
      setRouteMsg('Routing fehlgeschlagen. Pruefe API-Key oder Internet.')
    }
  }

  const toggleEV = () => {
    const map = mapRef.current
    const evLayer = evLayerRef.current
    if (!map || !evLayer) return
    if (map.hasLayer(evLayer)) {
      map.removeLayer(evLayer)
    } else {
      evLayer.addTo(map)
      const bounds = evLayer.getBounds()
      if (bounds && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [30, 30] })
      }
    }
  }

  const clearMap = () => {
    const map = mapRef.current
    const evLayer = evLayerRef.current
    if (routeRef.current && map) {
      map.removeLayer(routeRef.current)
      routeRef.current = null
    }
    if (map && evLayer && map.hasLayer(evLayer)) map.removeLayer(evLayer)
    setRouteMsg('')
  }

  const handleRedeem = () => {
    setPoints((p) => Math.max(0, p - 250))
  }

  const handleBestParking = () => {
    setParkingMsg('Closest low-traffic option: Garage C (EV) with chargers available.')
  }

  const handleReport = () => {
    setReportMsg(`Report sent: ${reportType.replace(/^\w/, (c) => c.toUpperCase())}. Thank you!`)
  }

  const toggleProfile = () => setProfileOpen((v) => !v)
  const goTo = (tab) => setActiveTab(tab)

  return (
    <>
      <header className="topbar" role="banner">
        <div className="brand">
          <span className="brand-dot"></span>
          <span>Smart Mobility - Driver</span>
        </div>
        <div className="spacer"></div>
        <button id="profileBtn" className="avatar" title="Profile" aria-haspopup="menu" aria-expanded={profileOpen} onClick={toggleProfile}></button>
      </header>

      <div className={`profile-menu ${profileOpen ? 'open' : ''}`} id="profileMenu" role="menu" aria-labelledby="profileBtn">
        <div className="profile-row">
          <div className="avatar" style={{ width: '28px', height: '28px', border: '1px solid rgba(79,209,197,.35)' }}></div>
          <div>
            <div>Driver</div>
            <small>{signedIn ? 'Signed in' : 'Signed out'}</small>
          </div>
        </div>
        <div className="profile-actions">
          <button className="btn" onClick={() => { setSignedIn((v) => !v); setProfileOpen(false) }}>
            {signedIn ? 'Sign out' : 'Sign in'}
          </button>
        </div>
      </div>

      <main className="wrap">
        <section className={`view ${activeTab === 'map' ? 'active' : ''}`} aria-hidden={activeTab !== 'map'} id="map-card">
          <article className="card map-card">
            <div className="body">
              <div id="map" ref={mapContainerRef}></div>
              <button className="map-fab" type="button" onClick={() => makeRoute(cityCenter, beach)} aria-label="Show route to parking">
                P
              </button>
            </div>
          </article>
        </section>

        <section className={`view ${activeTab === 'parking' ? 'active' : ''}`} aria-hidden={activeTab !== 'parking'} id="parking-card">
          <article className="card">
            <h2>Smart Parking</h2>
            <div className="body">
              <ul className="clean">
                <li>Nearby lot A - 12 spaces free</li>
                <li>Street B (200 m) - 3 spaces free</li>
                <li>Garage C (EV) - 4 spaces + chargers</li>
              </ul>
              <div className="infobar">
                <button className="btn" onClick={handleBestParking}>Best Option</button>
                <span className="pill">Live availability</span>
              </div>
              {parkingMsg && <div style={{ marginTop: '.6rem', color: 'var(--muted)' }}>{parkingMsg}</div>}
            </div>
          </article>
        </section>

        <section className={`view ${activeTab === 'rewards' ? 'active' : ''}`} aria-hidden={activeTab !== 'rewards'} id="rewards-card">
          <article className="card">
            <h2>Rewards</h2>
            <div className="body">
              <div className="reward-points">{points.toLocaleString()} pts</div>
              <ul className="clean">
                <li>No speeding: 7-day streak</li>
                <li>No double parking: 7-day streak</li>
              </ul>
              <div style={{ height: '.75rem' }}></div>
              <div className="controls">
                <button className="btn" onClick={handleRedeem}>Redeem Rewards</button>
              </div>
            </div>
          </article>
        </section>

        <section className={`view ${activeTab === 'report' ? 'active' : ''}`} aria-hidden={activeTab !== 'report'} id="reports-card">
          <article className="card">
            <h2>Report Hazard / Incident</h2>
            <div className="body">
              <div className="controls">
                <select
                  className="btn"
                  style={{ padding: '.45rem .6rem' }}
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                >
                  <option value="accident">Accident</option>
                  <option value="construction">Construction</option>
                  <option value="hazard">Road hazard</option>
                  <option value="blocked">Blocked parking</option>
                </select>
                <button className="btn" onClick={handleReport}>Send report</button>
              </div>
              <div style={{ marginTop: '.6rem', color: 'var(--muted)' }}>{reportMsg}</div>
            </div>
          </article>
        </section>

      </main>

      <nav className="bottom-nav" aria-label="Schnellnavigation">
        <button
          type="button"
          className={`nav-btn ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => goTo('map')}
          aria-pressed={activeTab === 'map'}
        >
          <span>Map</span>
        </button>
        <button
          type="button"
          className={`nav-btn ${activeTab === 'rewards' ? 'active' : ''}`}
          onClick={() => goTo('rewards')}
          aria-pressed={activeTab === 'rewards'}
        >
          <span>Rewards</span>
        </button>
        <button
          type="button"
          className={`nav-btn ${activeTab === 'report' ? 'active' : ''}`}
          onClick={() => goTo('report')}
          aria-pressed={activeTab === 'report'}
        >
          <span>Report</span>
        </button>
      </nav>
    </>
  )
}

export default App
