import { COLORS, VIOLATION_LEGEND_ITEMS } from './config.js';

// --- Marker Generators ---

export function makeAccidentMarker(a) {
  // Use a lightweight DivIcon so clusters remain performant
  const icon = L.divIcon({
    className: '',
    html: `<div class="accident ${COLORS.severityClass(a.severity)}"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
  return L.marker([a.lat, a.lng], { icon }).bindPopup(
    `<b>Accident (${a.severity})</b><br>${a.desc || ''}<br><small>${new Date(a.ts).toLocaleString()}</small>`
  );
}

export function makeViolationMarker(v) {
  const color = COLORS.violation(v.violation);
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

// --- Layer Styles ---

export const trafficStyle = {
  pointToLayer: (f, latlng) => L.circleMarker(latlng, {
    radius: 8,
    fillColor: COLORS.speed(f.properties.speed || 0),
    color: '#555',
    weight: 1,
    fillOpacity: 0.85
  }),
  style: f => ({
    color: COLORS.speed(f.properties.speed || 0),
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
};

export const parkingStyle = {
  pointToLayer: (f, latlng) => {
    const occ = f.properties.occupied / (f.properties.capacity || 1);
    return L.circleMarker(latlng, {
      radius: 10,
      fillColor: COLORS.occupancy(occ),
      color: '#555',
      weight: 2,
      fillOpacity: 0.85
    });
  },
  style: f => {
    const occ = f.properties.occupied / (f.properties.capacity || 1);
    return { color: COLORS.occupancy(occ), weight: 6, opacity: 0.9 };
  },
  onEachFeature: (f, layer) => {
    const occ = f.properties.occupied / (f.properties.capacity || 1);
    const pct = Math.round(occ * 100);
    const free = f.properties.capacity - f.properties.occupied;
    layer.bindPopup(`<b>${f.properties.name}</b><br>Occupied: ${pct}% (${f.properties.occupied}/${f.properties.capacity})<br>Free: ${free}`);
    layer.bindTooltip(`${f.properties.name}: ${pct}%`, { sticky: true });
  }
};

// --- Legend Logic ---

export function getLegendHTML(mode) {
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
    const rows = VIOLATION_LEGEND_ITEMS.map(item =>
      `<div class="row"><span class="box" style="background:${COLORS.violation(item.key)}"></span><span>${item.label}</span></div>`
    ).join('');
    return `
      <div class="title">Legend</div>
      <div><b>Violations</b></div>
      ${rows}
    `;
  }
  // Default: accidents
  return `
    <div class="title">Legend</div>
    <div><b>Accidents</b></div>
    <div class="row"><span class="box" style="background:#e74c3c"></span><span>Severe</span></div>
    <div class="row"><span class="box" style="background:#f1c40f"></span><span>Medium</span></div>
    <div class="row"><span class="box" style="background:#2ecc71"></span><span>Minor</span></div>
  `;
}
