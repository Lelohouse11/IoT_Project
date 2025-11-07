// Optional nutzt mapApi, falls später Routing zum „Best Parking“ getriggert werden soll.
export function initParking(mapApi) {
  const btnBest = document.getElementById('btnBestParking');
  const list    = document.getElementById('parkingList');

  btnBest?.addEventListener('click', () => {
    // Demo: pick first entry as „best“
    alert('Best parking: Nearby lot A – 12 spaces free (demo).');
    // Beispiel: später mapApi.makeRoute(...) zu Parking-Koordinaten
  });

  console.assert(!!list, 'Parking list should exist.');
}
