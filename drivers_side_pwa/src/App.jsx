import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import './App.css'

const cityCenter = [38.2464, 21.7346]
const beach = [38.2588, 21.7347]
function App() {
  const [profileOpen, setProfileOpen] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [activeTab, setActiveTab] = useState('map')
  const [points, setPoints] = useState(1250)
  const [reportType, setReportType] = useState('accident')
  const [reportMsg, setReportMsg] = useState('Help improve the map by reporting issues.')

  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const routeRef = useRef(null)

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

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
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
    if (!key) return

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

  const handleRedeem = () => {
    setPoints((p) => Math.max(0, p - 250))
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
