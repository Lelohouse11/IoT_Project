import { CONFIG, COLORS } from './config.js';
import { makeAccidentMarker, makeViolationMarker, trafficStyle, parkingStyle, getLegendHTML } from './map_helpers.js';
import { updateGrafanaTime, resetGrafanaTime } from './grafana.js';

// Initialize the Leaflet map, live accident overlay, and polling logic.
// Exposes a small API on window.MapAPI for future adapters (MQTT, SSE).
export function initMap() {
  // Base map (OSM)
  const map = L.map('map', { zoomControl: true, scrollWheelZoom: true }).setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // --- Dummy data (Patras area) ---
  const roads = { type: 'FeatureCollection', features: [] };
  const zones = { type: 'FeatureCollection', features: [] };

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

  // --- Traffic: styled GeoJSON lines ---
  const trafficLayer = L.geoJSON(roads, trafficStyle);

  // --- Parking: polygons styled by occupancy ---
  const parkingLayer = L.geoJSON(zones, parkingStyle);

  // --- Layer control ---
  L.control.layers({ 'Accidents': accidentCluster, 'Traffic': trafficLayer, 'Parking': parkingLayer, 'Violations': violationCluster }, {}, { collapsed: false }).addTo(map);

  // Start with a single default overlay (accidents)
  accidentCluster.addTo(map);

  // --- Legend ---
  const legend = L.control({ position: 'bottomright' });
  legend.onAdd = function() {
    const div = L.DomUtil.create('div', 'legend');
    div.innerHTML = getLegendHTML('accidents');
    return div;
  };
  legend.addTo(map);

  // Dynamic legend content in English based on selected layer
  const legendNode = document.querySelector('.legend');
  function setLegend(mode) { if (legendNode) legendNode.innerHTML = getLegendHTML(mode); }
  
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
    map.setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM, { animate: true });
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
    accidentCluster.clearLayers();
    items.forEach(a => accidentCluster.addLayer(makeAccidentMarker(a)));
  }

  // Optional: diff-based updates (upsert/remove) for streaming sources
  const accidentIndex = new Map(); // id -> { marker, lastSeen }
  const violationIndex = new Map(); // id -> { marker, lastSeen }

  function upsertItem(item, index, cluster, markerFactory, colorFunc, type) {
    const now = Date.now();
    const entry = index.get(item.id);
    if (entry) {
      entry.marker.setLatLng([item.lat, item.lng]);
      
      // Update icon and popup content
      if (type === 'accident') {
         entry.marker.setIcon(L.divIcon({
            className: '',
            html: `<div class="accident ${COLORS.severityClass(item.severity)}"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
         }));
         entry.marker.setPopupContent(`<b>Accident (${item.severity})</b><br>${item.desc || ''}<br><small>${item.ts ? new Date(item.ts).toLocaleString() : ''}</small>`);
      } else if (type === 'violation') {
         entry.marker.setIcon(L.divIcon({
            className: '',
            html: `<div class="violation" style="background:${COLORS.violation(item.violation)}"></div>`,
            iconSize: [18, 18],
            iconAnchor: [9, 9]
         }));
         entry.marker.setPopupContent(`<b>Violation</b><br>${item.violation || 'unknown'}<br>${item.description || ''}<br><small>${item.ts ? new Date(item.ts).toLocaleString() : ''}</small>`);
      }
      
      entry.lastSeen = now;
    } else {
      const m = markerFactory(item);
      index.set(item.id, { marker: m, lastSeen: now });
      cluster.addLayer(m);
    }
  }

  function upsertAccident(a) {
    upsertItem(a, accidentIndex, accidentCluster, makeAccidentMarker, null, 'accident');
  }

  function upsertViolation(v) {
    upsertItem(v, violationIndex, violationCluster, makeViolationMarker, null, 'violation');
  }

  function removeAccidentById(id) {
    const entry = accidentIndex.get(id);
    if (entry) { accidentCluster.removeLayer(entry.marker); accidentIndex.delete(id); }
  }

  function pruneOldItems(index, cluster, ttl) {
    const now = Date.now();
    for (const [id, entry] of index.entries()) {
      if (now - entry.lastSeen > ttl) {
        cluster.removeLayer(entry.marker);
        index.delete(id);
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
  const apiStatusEl = document.getElementById('apiStatus');
  const nextRefreshEl = document.getElementById('nextRefresh');
  const btnRefreshNow = document.getElementById('btnRefreshNow');
  
  // Filter State
  let filterStart = null;
  let filterEnd = null;

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

  function getQueryParams(windowParam) {
    let qs = `?window=${encodeURIComponent(windowParam)}`;
    if (filterStart && filterEnd) {
      qs += `&start_time=${encodeURIComponent(filterStart)}&end_time=${encodeURIComponent(filterEnd)}`;
    }
    return qs;
  }

  async function fetchRecentAccidents() {
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/accidents/recent${getQueryParams(CONFIG.API_WINDOW)}`);
      if (!res.ok) { setApiStatus('error', `HTTP ${res.status}`); return; }
      const items = await res.json();
      if (Array.isArray(items)) {
        // If filtering, clear old items first to show only range
        if (filterStart) {
            accidentCluster.clearLayers();
            accidentIndex.clear();
        }
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
      const res = await fetch(`${CONFIG.API_BASE}/api/traffic/recent${getQueryParams(CONFIG.API_WINDOW)}`);
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
      const res = await fetch(`${CONFIG.API_BASE}/api/parking/recent${getQueryParams(CONFIG.API_WINDOW)}`);
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
      const res = await fetch(`${CONFIG.API_BASE}/api/violations/recent${getQueryParams(CONFIG.VIOLATION_WINDOW)}`);
      if (!res.ok) return;
      const items = await res.json();
      if (Array.isArray(items)) {
        if (filterStart) {
            violationCluster.clearLayers();
            violationIndex.clear();
        }
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
    if (filterStart) {
        nextRefreshEl.textContent = "Paused (Filter)";
        return;
    }
    const remainingMs = Math.max(0, nextRefreshAt - Date.now());
    const s = Math.ceil(remainingMs / 1000);
    nextRefreshEl.textContent = `Next: ${s}s`;
  }

  function startAutoRefresh() {
    if (fetchTimer) clearInterval(fetchTimer);
    nextRefreshAt = Date.now() + CONFIG.REFRESH_MS;
    fetchTimer = setInterval(() => {
      fetchRecentAccidents();
      fetchRecentTraffic();
      fetchRecentViolations();
      nextRefreshAt = Date.now() + CONFIG.REFRESH_MS;
    }, CONFIG.REFRESH_MS);
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(updateCountdown, 1000);
    updateCountdown();
  }

  function stopAutoRefresh() {
    if (fetchTimer) clearInterval(fetchTimer);
    if (countdownTimer) clearInterval(countdownTimer);
    fetchTimer = null;
    countdownTimer = null;
    if (nextRefreshEl) nextRefreshEl.textContent = "Paused";
  }

  // Manual refresh button
  if (btnRefreshNow) {
    btnRefreshNow.addEventListener('click', () => {
      fetchRecentAccidents();
      fetchRecentTraffic();
      fetchRecentParking();
      fetchRecentViolations();
      if (!filterStart) startAutoRefresh(); // reset cadence and countdown only if not filtering
    });
  }

  // Filter UI Logic
  const btnApplyFilter = document.getElementById('btnApplyFilter');
  const btnClearFilter = document.getElementById('btnClearFilter');
  const inputStart = document.getElementById('filterStart');
  const inputEnd = document.getElementById('filterEnd');

  if (btnApplyFilter && btnClearFilter) {
    btnApplyFilter.addEventListener('click', () => {
        const s = inputStart.value;
        const e = inputEnd.value;
        if (s && e) {
            filterStart = new Date(s).toISOString();
            filterEnd = new Date(e).toISOString();
            stopAutoRefresh();
            
            // Update Grafana
            updateGrafanaTime(new Date(s).getTime(), new Date(e).getTime());

            // Fetch filtered data
            fetchRecentAccidents();
            fetchRecentTraffic();
            fetchRecentParking();
            fetchRecentViolations();
        } else {
            alert("Please select both start and end times.");
        }
    });

    btnClearFilter.addEventListener('click', () => {
        inputStart.value = '';
        inputEnd.value = '';
        filterStart = null;
        filterEnd = null;
        
        // Reset Grafana
        resetGrafanaTime();

        // Clear map and fetch live data
        accidentCluster.clearLayers();
        accidentIndex.clear();
        violationCluster.clearLayers();
        violationIndex.clear();
        
        fetchRecentAccidents();
        fetchRecentTraffic();
        fetchRecentParking();
        fetchRecentViolations();
        startAutoRefresh();
    });
  }

  // Prune old accidents periodically (only if not filtering)
  setInterval(() => { 
      if (!filterStart) {
        pruneOldItems(accidentIndex, accidentCluster, CONFIG.ACCIDENT_TTL_MS); 
        pruneOldItems(violationIndex, violationCluster, CONFIG.VIOLATION_TTL_MS); 
      }
  }, CONFIG.PRUNE_MS);

  // Kick off
  fetchRecentAccidents();
  fetchRecentTraffic();
  fetchRecentParking();
  fetchRecentViolations();
  startAutoRefresh();
}
