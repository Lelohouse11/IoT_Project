// Initialisiert Leaflet-Map, Routing und EV-Layer.
// Gibt Helfer zurück, die von anderen Modulen genutzt werden können (optional).

export function initMap() {
  // Base map
  const map = L.map('map', { zoomControl: true, scrollWheelZoom: true }).setView([38.2464, 21.7346], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // Routing (OSRM demo server)
  let router;
  function makeRoute(a, b) {
    if (router) { map.removeControl(router); router = null; }
    router = L.Routing.control({
      waypoints: [a, b],
      router: L.Routing.osrmv1({ serviceUrl: 'https://router.project-osrm.org/route/v1' }),
      showAlternatives: false,
      addWaypoints: false,
      draggableWaypoints: false,
      fitSelectedRoutes: true,
      lineOptions: { addWaypoints: false }
    }).addTo(map);
  }

  // Demo points (Patras)
  const cityCenter = L.latLng(38.2464, 21.7346);
  const beach      = L.latLng(38.2588, 21.7347);

  // EV chargers (use FeatureGroup so we can safely getBounds)
  const evLayer = L.featureGroup();
  const evPoints = [
    [38.2488, 21.7301],
    [38.2441, 21.7398],
    [38.2532, 21.7443],
    [38.2505, 21.7280]
  ];
  evPoints.forEach(([lat, lng]) =>
    L.circleMarker([lat, lng], { radius: 7, weight: 2, color: '#4fd1c5' })
      .bindTooltip('EV Charger')
      .addTo(evLayer)
  );

  // UI wiring
  document.getElementById('btnRouteHome')?.addEventListener('click', () => makeRoute(cityCenter, beach));

  document.getElementById('btnNearbyEV')?.addEventListener('click', () => {
    if (map.hasLayer(evLayer)) {
      map.removeLayer(evLayer);
    } else {
      evLayer.addTo(map);
      const layers = evLayer.getLayers();
      if (layers && layers.length) {
        const bounds = evLayer.getBounds();
        if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [30, 30] });
      }
    }
  });

  document.getElementById('btnClear')?.addEventListener('click', () => {
    if (router) { map.removeControl(router); router = null; }
    if (map.hasLayer(evLayer)) map.removeLayer(evLayer);
  });

  // Optional: Exporte für andere Module
  return {
    map,
    makeRoute,
    cityCenter,
    beach,
    evLayer
  };
}
