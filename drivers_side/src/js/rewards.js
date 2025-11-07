export function initRewards() {
  const btnRedeem    = document.getElementById('btnRedeem');
  const btnSafety    = document.getElementById('btnSafetyTest');
  const pointsEl     = document.getElementById('points');
  const streakListEl = document.getElementById('streakList');

  btnRedeem?.addEventListener('click', () => {
    alert('Redeem: 500 pts for Pool/City partner discount (demo).');
    // Demo: Punkte visuell reduzieren
    if (pointsEl) pointsEl.textContent = '750 pts';
  });

  btnSafety?.addEventListener('click', () => {
    alert('Weather alert: heavy rain ahead. Reduce speed.');
  });

  // Mini-„Test“ (Konsole): prüfen, ob Elemente existieren
  console.assert(!!pointsEl && !!streakListEl, 'Rewards UI should exist.');
}
