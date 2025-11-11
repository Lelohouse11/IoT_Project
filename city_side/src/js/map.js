// Initialize the Leaflet map, live accident overlay, and polling logic.
// Exposes a small API on window.MapAPI for future adapters (MQTT, SSE).
export function initMap() {
  // --- Config ---
  const REFRESH_MS = 15000;           // auto-refresh interval for accident fetch
  const API_WINDOW = '10m';           // how far back to look for active accidents
  const ACCIDENT_TTL_MS = 5 * 60 * 1000; // keep accidents on map this long after last seen
  const PRUNE_MS = 30000;             // prune cadence
  // Base map (OSM)
  const map = L.map('map', { zoomControl: true, scrollWheelZoom: true }).setView([38.2464, 21.7346], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // --- Dummy data (Patras area) ---
  const accidents = [
    { id: 1, severity: 'minor',  ts: '2025-01-01T08:15:00Z', lat: 38.2469, lng: 21.7320, desc: 'Minor collision' },
    { id: 2, severity: 'major',  ts: '2025-01-01T08:25:00Z', lat: 38.2435, lng: 21.7395, desc: 'Multi-vehicle accident' },
    { id: 3, severity: 'medium', ts: '2025-01-01T08:40:00Z', lat: 38.2512, lng: 21.7412, desc: 'Blocked lane' },
  ];

  const roads = {
    type: 'FeatureCollection',
    features: [
      { type: 'Feature', properties: { id:'R-001', ref:'Avenue 1', speed: 65 }, geometry: { type:'LineString', coordinates: [[21.726,38.244],[21.735,38.246],[21.745,38.248]] } },
      { type: 'Feature', properties: { id:'R-002', ref:'Avenue 2', speed: 22 }, geometry: { type:'LineString', coordinates: [[21.742,38.242],[21.747,38.244],[21.754,38.246]] } }
    ]
  };

  const zones = {
    type: 'FeatureCollection',
    features: [
      { type:'Feature', properties:{ id:'P-001', name:'Parking Center', capacity:180, occupied:120 }, geometry:{ type:'Polygon', coordinates:[[[21.731,38.2448],[21.734,38.2448],[21.734,38.2468],[21.731,38.2468],[21.731,38.2448]]] } },
      { type:'Feature', properties:{ id:'P-002', name:'Harbor Lot',    capacity: 90,  occupied: 30  }, geometry:{ type:'Polygon', coordinates:[[[21.741,38.2475],[21.744,38.2475],[21.744,38.2492],[21.741,38.2492],[21.741,38.2475]]] } }
    ]
  };

  // --- Helpers ---
  const speedToColor = v => (v>=70?'#2ecc71':v>=45?'#f1c40f':v>=25?'#e67e22':'#e74c3c');
  const occColor = frac => (frac<=0.5?'#2ecc71':frac<=0.8?'#f39c12':'#e74c3c');
  const severityClass = s => (s==='major'?'major':s==='medium'?'medium':'minor');

  // --- Accidents: MarkerCluster layer ---
  const accidentCluster = L.markerClusterGroup({
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
  // Index and helpers are declared later; seed initial points via upsert
  // to ensure TTL bookkeeping works for them as well.
  // We'll temporarily store and apply after function definitions.
  const seedAccidents = [...accidents];

  // --- Traffic: styled GeoJSON lines ---
  const trafficLayer = L.geoJSON(roads, {
    style: f => ({ color: speedToColor(f.properties.speed), weight: 6, opacity: 0.85 }),
    onEachFeature: (f, layer) => layer.bindPopup(`<b>${f.properties.ref || 'Segment'}</b><br>Speed: ${f.properties.speed} km/h`)
  });

  // --- Parking: polygons styled by occupancy ---
  const parkingLayer = L.geoJSON(zones, {
    style: f => {
      const occ = f.properties.occupied / f.properties.capacity;
      return { fillColor: occColor(occ), color: '#555', weight: 1, fillOpacity: 0.6 };
    },
    onEachFeature: (f, layer) => {
      const occ = f.properties.occupied / f.properties.capacity;
      const pct = Math.round(occ * 100);
      const free = f.properties.capacity - f.properties.occupied;
      layer.bindPopup(`<b>${f.properties.name}</b><br>Occupied: ${pct}% (${f.properties.occupied}/${f.properties.capacity})<br>Free: ${free}`);
      layer.bindTooltip(`${f.properties.name}: ${pct}%`, { sticky: true });
    }
  });

  // --- Layer control ---
  L.control.layers({ 'Accidents': accidentCluster, 'Traffic': trafficLayer, 'Parking': parkingLayer }, {}, { collapsed: false }).addTo(map);

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
      <div class="row"><span class="box" style="background:#2ecc71"></span><span>≤ 50% occupied</span></div>
      <div class="row"><span class="box" style="background:#f39c12"></span><span>≤ 80% occupied</span></div>
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
  });

  // --- Fit bounds to all overlays ---
  const all = L.featureGroup([accidentCluster, trafficLayer, parkingLayer]);
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

  // Expose API for future adapters (e.g., MQTT handler)
  window.MapAPI = {
    map,
    layers: { accidentCluster, trafficLayer, parkingLayer },
    replaceTraffic,
    replaceParking,
    replaceAccidents,
    upsertAccident,
    removeAccidentById
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
        // Incremental replace to allow TTL-based pruning
        const seen = new Set();
        for (const a of items) { seen.add(a.id); upsertAccident(a); }
        // Note: pruning is handled separately by pruneOldAccidents()
        const ts = new Date().toLocaleTimeString();
        setApiStatus('ok', `Last update ${ts}`);
      }
    } catch (_) {
      setApiStatus('error');
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
      startAutoRefresh(); // reset cadence and countdown
    });
  }
  // Prune old accidents periodically
  setInterval(pruneOldAccidents, PRUNE_MS);
  // Seed initial markers via upsert
  seedAccidents.forEach(upsertAccident);
  // Kick off
  fetchRecentAccidents();
  startAutoRefresh();
}