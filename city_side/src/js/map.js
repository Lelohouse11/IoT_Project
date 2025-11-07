export function initMap() {
  const map = L.map('map', { zoomControl: true, scrollWheelZoom: true }).setView([38.2464, 21.7346], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const demoMarker = L.marker([38.2464, 21.7346]).addTo(map);
  demoMarker.bindPopup('<b>City Center</b><br/>Patras');

  document.getElementById('locBtn')?.addEventListener('click', () => {
    map.setView([38.2464, 21.7346], 13, { animate: true });
    demoMarker.openPopup();
  });
}
