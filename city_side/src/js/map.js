// Initialize the Leaflet map, live accident overlay, and polling logic.
// Exposes a small API on window.MapAPI for future adapters (MQTT, SSE).
export function initMap() {
  // --- Config ---
  const REFRESH_MS = 15000;           // auto-refresh interval for accident fetch
  const API_WINDOW = '10m';           // how far back to look for active accidents
  const VIOLATION_WINDOW = '5m';      // lookback for traffic violations
  const ACCIDENT_TTL_MS = 5 * 60 * 1000; // keep accidents on map this long after last seen
  const VIOLATION_TTL_MS = 5 * 60 * 1000;
  const PRUNE_MS = 30000;             // prune cadence
  // Base map (OSM)
  const map = L.map('map', { zoomControl: true, scrollWheelZoom: true }).setView([38.2464, 21.7346], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // --- Dummy data (Patras area) ---

  const roads = { type: 'FeatureCollection', features: [] };
  const zones = { type: 'FeatureCollection', features: [] };

  // --- Helpers ---
  const speedToColor = v => (v>=70?'#2ecc71':v>=45?'#f1c40f':v>=25?'#e67e22':'#e74c3c');
  const occColor = frac => (frac<=0.5?'#2ecc71':frac<=0.8?'#f39c12':'#e74c3c');
  const severityClass = s => (s==='major'?'major':s==='medium'?'medium':'minor');
  const violationColor = type => ({
    'double-parking': '#e67e22',
    'red-light': '#e74c3c',
    'no-stopping': '#f1c40f',
    'near-intersection': '#3498db'
  }[type] || '#1abc9c');
  const violationLegendItems = [
    { key: 'double-parking', label: 'Double parking' },
    { key: 'red-light', label: 'Red light' },
    { key: 'no-stopping', label: 'No stopping' },
    { key: 'near-intersection', label: 'Near intersection' }
  ];

  // --- Accidents: MarkerCluster layer ---
  const accidentCluster = L.markerClusterGroup({
    disableClusteringAtZoom: 16,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    chunkedLoading: true
  });
  const violationCluster = L.markerClusterGroup({
    disableClusteringAtZoom: 16,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    chunkedLoading: true
  });

  function makeAccidentMarker(a) {
    // Use a lightweight DivIcon so clusters remain performant
    const icon = L.divIcon({
      className: '',
      html: `<div class="accident ${severityClass(a.severity)}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
    return L.marker([a.lat, a.lng], { icon }).bindPopup(
      `<b>Accident (${a.severity})</b><br>${a.desc || ''}<br><small>${new Date(a.ts).toLocaleString()}</small>`
    );
  }
  function makeViolationMarker(v) {
    const color = violationColor(v.violation);
    const icon = L.divIcon({
      className: '',
      html: `<div class="violation" style="background:${color}"></div>`,
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });
    return L.marker([v.lat, v.lng], { icon }).bindPopup(
      `<b>Violation</b><br>${v.violation || 'unknown'}<br>${v.description || ''}<br><small>${new Date(v.ts).toLocaleString()}</small>`
    );
  }
  // --- Traffic: styled GeoJSON lines ---
  const trafficLayer = L.geoJSON(roads, {
    pointToLayer: (f, latlng) => L.circleMarker(latlng, {
      radius: 8,
      fillColor: speedToColor(f.properties.speed || 0),
      color: '#555',
      weight: 1,
      fillOpacity: 0.85
    }),
    style: f => ({
      color: speedToColor(f.properties.speed || 0),
      weight: 6,
      opacity: 0.55,
      lineCap: 'round'
    }),
    onEachFeature: (f, layer) => {
      const ref = f.properties.ref || 'Segment';
      const speed = f.properties.speed ?? '?';
      const density = f.properties.density ?? '?';
      const occupancy = f.properties.occupancy ?? '?';
      const congestion = f.properties.congestion || '';
      layer.bindPopup(`<b>${ref}</b><br>Speed: ${speed} km/h<br>Density: ${density}<br>Occupancy: ${Math.round((occupancy||0)*100)}%<br>${congestion}`);
    }
  });

  // --- Parking: polygons styled by occupancy ---
  const parkingLayer = L.geoJSON(zones, {
    pointToLayer: (f, latlng) => {
      const occ = f.properties.occupied / (f.properties.capacity || 1);
      return L.circleMarker(latlng, {
        radius: 10,
        fillColor: occColor(occ),
        color: '#555',
        weight: 2,
        fillOpacity: 0.85
      });
    },
    style: f => {
      const occ = f.properties.occupied / (f.properties.capacity || 1);
      return { color: occColor(occ), weight: 6, opacity: 0.9 };
    },
    onEachFeature: (f, layer) => {
      const occ = f.properties.occupied / (f.properties.capacity || 1);
      const pct = Math.round(occ * 100);
      const free = f.properties.capacity - f.properties.occupied;
      layer.bindPopup(`<b>${f.properties.name}</b><br>Occupied: ${pct}% (${f.properties.occupied}/${f.properties.capacity})<br>Free: ${free}`);
      layer.bindTooltip(`${f.properties.name}: ${pct}%`, { sticky: true });
    }
  });

  // --- Layer control ---
  L.control.layers({ 'Accidents': accidentCluster, 'Traffic': trafficLayer, 'Parking': parkingLayer, 'Violations': violationCluster }, {}, { collapsed: false }).addTo(map);

  // Using base layer radios for mutual exclusivity; no overlay toggling needed

  // Start with a single default overlay (accidents)
  accidentCluster.addTo(map);

  // --- Legend ---
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function() {
    const div = L.DomUtil.create('div', 'legend');
    div.innerHTML = `
      <div class="title">Legend</div>
      <div><b>Accidents</b></div>
      <div class="row"><span class="box" style="background:#e74c3c"></span><span>Severe</span></div>
      <div class="row"><span class="box" style="background:#f1c40f"></span><span>Medium</span></div>
      <div class="row"><span class="box" style="background:#2ecc71"></span><span>Minor</span></div>
      <div style="height:6px"></div>
      <div><b>Traffic</b></div>
      <div class="row"><span class="box" style="background:#2ecc71"></span><span>Free flow</span></div>
      <div class="row"><span class="box" style="background:#f1c40f"></span><span>Slow</span></div>
      <div class="row"><span class="box" style="background:#e67e22"></span><span>Heavy</span></div>
      <div class="row"><span class="box" style="background:#e74c3c"></span><span>Jam</span></div>
      <div style="height:6px"></div>
      <div><b>Parking occupancy</b></div>
      <div class="row"><span class="box" style="background:#2ecc71"></span><span>&lt;= 50% occupied</span></div>
      <div class="row"><span class="box" style="background:#f39c12"></span><span>&lt;= 80% occupied</span></div>
      <div class="row"><span class="box" style="background:#e74c3c"></span><span>> 80% occupied</span></div>
    `;
    return div;
  };
  legend.addTo(map);

  // Dynamic legend content in English based on selected layer
  const legendNode = document.querySelector('.legend');
  function legendHTML(mode) {
    if (mode === 'traffic') {
      return `
        <div class="title">Legend</div>
        <div><b>Traffic</b></div>
        <div class="row"><span class="box" style="background:#2ecc71"></span><span>Free flow</span></div>
        <div class="row"><span class="box" style="background:#f1c40f"></span><span>Slow</span></div>
        <div class="row"><span class="box" style="background:#e67e22"></span><span>Heavy</span></div>
        <div class="row"><span class="box" style="background:#e74c3c"></span><span>Jam</span></div>
      `;
    }
    if (mode === 'parking') {
      return `
        <div class="title">Legend</div>
        <div><b>Parking occupancy</b></div>
        <div class="row"><span class="box" style="background:#2ecc71"></span><span><= 50% occupied</span></div>
        <div class="row"><span class="box" style="background:#f39c12"></span><span><= 80% occupied</span></div>
        <div class="row"><span class="box" style="background:#e74c3c"></span><span>> 80% occupied</span></div>
      `;
    }
    if (mode === 'violations') {
      const rows = violationLegendItems.map(item =>
        `<div class="row"><span class="box" style="background:${violationColor(item.key)}"></span><span>${item.label}</span></div>`
      ).join('');
      return `
        <div class="title">Legend</div>
        <div><b>Violations</b></div>
        ${rows}
      `;
    }
    return `
      <div class="title">Legend</div>
      <div><b>Accidents</b></div>
      <div class="row"><span class="box" style="background:#e74c3c"></span><span>Severe</span></div>
      <div class="row"><span class="box" style="background:#f1c40f"></span><span>Medium</span></div>
      <div class="row"><span class="box" style="background:#2ecc71"></span><span>Minor</span></div>
    `;
  }
  function setLegend(mode) { if (legendNode) legendNode.innerHTML = legendHTML(mode); }
  setLegend('accidents');
  map.on('baselayerchange', function(e){
    if (e.name === 'Accidents') setLegend('accidents');
    else if (e.name === 'Traffic') setLegend('traffic');
    else if (e.name === 'Parking') setLegend('parking');
    else if (e.name === 'Violations') setLegend('violations');
  });

  // --- Fit bounds to all overlays ---
  const all = L.featureGroup([accidentCluster, trafficLayer, parkingLayer, violationCluster]);
  const bounds = all.getBounds();
  if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] });

  // --- UI: Center button keeps working ---
  document.getElementById('locBtn')?.addEventListener('click', () => {
    map.setView([38.2464, 21.7346], 13, { animate: true });
  });

  // --- Update API for future MQTT/Influx integration ---
  function replaceTraffic(newGeoJSON) {
    trafficLayer.clearLayers();
    trafficLayer.addData(newGeoJSON);
  }
  function replaceParking(newGeoJSON) {
    parkingLayer.clearLayers();
    parkingLayer.addData(newGeoJSON);
  }
  function replaceAccidents(items) {
    // Full replace is available but not used in polling path (we prefer incremental updates)
    accidentCluster.clearLayers();
    items.forEach(a => accidentCluster.addLayer(makeAccidentMarker(a)));
  }

  // Optional: diff-based updates (upsert/remove) for streaming sources
  const accidentIndex = new Map(); // id -> { marker, lastSeen }
  const violationIndex = new Map(); // id -> { marker, lastSeen }
  function upsertAccident(a) {
    const now = Date.now();
    const entry = accidentIndex.get(a.id);
    if (entry) {
      entry.marker
        .setLatLng([a.lat, a.lng])
        .setIcon(L.divIcon({ className: '', html: `<div class="accident ${severityClass(a.severity)}"></div>`, iconSize: [20,20], iconAnchor:[10,10] }))
        .setPopupContent(`<b>Accident (${a.severity})</b><br>${a.desc || ''}<br><small>${a.ts ? new Date(a.ts).toLocaleString() : ''}</small>`);
      entry.lastSeen = now;
    } else {
      const m = makeAccidentMarker(a);
      accidentIndex.set(a.id, { marker: m, lastSeen: now });
      accidentCluster.addLayer(m);
    }
  }
  function removeAccidentById(id) {
    const entry = accidentIndex.get(id);
    if (entry) { accidentCluster.removeLayer(entry.marker); accidentIndex.delete(id); }
  }
  function pruneOldAccidents() {
    // Remove markers that have not been seen for ACCIDENT_TTL_MS
    const now = Date.now();
    for (const [id, entry] of accidentIndex.entries()) {
      if (now - entry.lastSeen > ACCIDENT_TTL_MS) {
        accidentCluster.removeLayer(entry.marker);
        accidentIndex.delete(id);
      }
    }
  }
  function upsertViolation(v) {
    const now = Date.now();
    const entry = violationIndex.get(v.id);
    if (entry) {
      entry.marker
        .setLatLng([v.lat, v.lng])
        .setIcon(L.divIcon({ className: '', html: `<div class="violation" style="background:${violationColor(v.violation)}"></div>`, iconSize: [18,18], iconAnchor:[9,9] }))
        .setPopupContent(`<b>Violation</b><br>${v.violation || 'unknown'}<br>${v.description || ''}<br><small>${v.ts ? new Date(v.ts).toLocaleString() : ''}</small>`);
      entry.lastSeen = now;
    } else {
      const m = makeViolationMarker(v);
      violationIndex.set(v.id, { marker: m, lastSeen: now });
      violationCluster.addLayer(m);
    }
  }
  function pruneOldViolations() {
    const now = Date.now();
    for (const [id, entry] of violationIndex.entries()) {
      if (now - entry.lastSeen > VIOLATION_TTL_MS) {
        violationCluster.removeLayer(entry.marker);
        violationIndex.delete(id);
      }
    }
  }

  // Expose API for future adapters (e.g., MQTT handler)
  window.MapAPI = {
    map,
    layers: { accidentCluster, trafficLayer, parkingLayer, violationCluster },
    replaceTraffic,
    replaceParking,
    replaceAccidents,
    upsertAccident,
    removeAccidentById,
    upsertViolation
  };

  // --- Poll backend API for live accidents (optional) ---
  const API_BASE = window.APP_API_BASE || ""; // e.g., set to "http://localhost:8000" if needed
  const apiStatusEl = document.getElementById('apiStatus');
  const nextRefreshEl = document.getElementById('nextRefresh');
  const btnRefreshNow = document.getElementById('btnRefreshNow');
  function setApiStatus(state, note) {
    if (!apiStatusEl) return;
    apiStatusEl.classList.remove('success', 'error', 'warn');
    if (state === 'ok') {
      apiStatusEl.classList.add('success');
      apiStatusEl.textContent = 'API: OK';
    } else if (state === 'error') {
      apiStatusEl.classList.add('error');
      apiStatusEl.textContent = 'API: offline';
    } else {
      apiStatusEl.classList.add('warn');
      apiStatusEl.textContent = 'API: checking…';
    }
    if (note) apiStatusEl.title = note;
  }
  setApiStatus('checking');
  async function fetchRecentAccidents() {
    try {
      const res = await fetch(`${API_BASE}/api/accidents/recent?window=${encodeURIComponent(API_WINDOW)}`);
      if (!res.ok) { setApiStatus('error', `HTTP ${res.status}`); return; }
      const items = await res.json();
      if (Array.isArray(items)) {
        for (const a of items) { upsertAccident(a); }
        const ts = new Date().toLocaleTimeString();
        setApiStatus('ok', `Last update ${ts}`);
      }
    } catch (_) {
      setApiStatus('error');
    }
  }
  async function fetchRecentTraffic() {
    try {
      const res = await fetch(`${API_BASE}/api/traffic/recent?window=${encodeURIComponent(API_WINDOW)}`);
      if (!res.ok) return;
      const items = await res.json();
      if (Array.isArray(items)) {
        const fc = {
          type: 'FeatureCollection',
          features: items.map(t => {
            const geometry = t.geometry && t.geometry.type ? t.geometry : { type: 'Point', coordinates: [t.lng, t.lat] };
            return {
              type: 'Feature',
              properties: {
                ref: t.ref_segment || t.id,
                speed: t.avg_speed,
                density: t.density,
                occupancy: t.occupancy,
                congestion: t.congestion || (t.congested ? 'congested' : 'freeFlow')
              },
              geometry
            };
          })
        };
        replaceTraffic(fc);
      }
    } catch (_) {
      /* ignore traffic fetch errors to avoid breaking accident status */
    }
  }
  async function fetchRecentParking() {
    try {
      const res = await fetch(`${API_BASE}/api/parking/recent?window=${encodeURIComponent(API_WINDOW)}`);
      if (!res.ok) return;
      const items = await res.json();
      if (Array.isArray(items)) {
        const fc = {
          type: 'FeatureCollection',
          features: items.map(p => ({
            type: 'Feature',
            properties: {
              id: p.id,
              name: p.street || p.id,
              capacity: p.total_spots,
              occupied: p.occupied_spots,
              available: p.available_spots,
              status: p.status || ''
            },
            geometry: {
              type: p.geometry?.type || 'Point',
              coordinates: p.geometry?.coordinates || [p.lng, p.lat]
            }
          }))
        };
        replaceParking(fc);
      }
    } catch (_) {
      /* ignore parking fetch errors to avoid breaking accident status */
    }
  }
  async function fetchRecentViolations() {
    try {
      const res = await fetch(`${API_BASE}/api/violations/recent?window=${encodeURIComponent(VIOLATION_WINDOW)}`);
      if (!res.ok) return;
      const items = await res.json();
      if (Array.isArray(items)) {
        for (const v of items) { upsertViolation(v); }
      }
    } catch (_) {
      /* ignore violation fetch errors */
    }
  }
  // Countdown & scheduling
  let nextRefreshAt = 0;
  let fetchTimer = null;
  let countdownTimer = null;
  function updateCountdown() {
    if (!nextRefreshEl) return;
    const remainingMs = Math.max(0, nextRefreshAt - Date.now());
    const s = Math.ceil(remainingMs / 1000);
    nextRefreshEl.textContent = `Next: ${s}s`;
  }
  function startAutoRefresh() {
    if (fetchTimer) clearInterval(fetchTimer);
    nextRefreshAt = Date.now() + REFRESH_MS;
    fetchTimer = setInterval(() => {
      fetchRecentAccidents();
      fetchRecentTraffic();
      fetchRecentViolations();
      nextRefreshAt = Date.now() + REFRESH_MS;
    }, REFRESH_MS);
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(updateCountdown, 1000);
    updateCountdown();
  }
  // Manual refresh button
  if (btnRefreshNow) {
    btnRefreshNow.addEventListener('click', () => {
      fetchRecentAccidents();
      fetchRecentTraffic();
      fetchRecentParking();
      fetchRecentViolations();
      startAutoRefresh(); // reset cadence and countdown
    });
  }
  // Prune old accidents periodically
  setInterval(() => { pruneOldAccidents(); pruneOldViolations(); }, PRUNE_MS);
  // Kick off
  fetchRecentAccidents();
  fetchRecentTraffic();
  fetchRecentParking();
  fetchRecentViolations();
  startAutoRefresh();
}
