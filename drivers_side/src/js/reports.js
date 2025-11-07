export function initReports() {
  const btnReport  = document.getElementById('btnReport');
  const typeSelect = document.getElementById('reportType');
  const msgEl      = document.getElementById('reportMsg');

  btnReport?.addEventListener('click', () => {
    const type = typeSelect?.value || 'unknown';
    if (msgEl) msgEl.textContent = `Report submitted: ${type}. Thank you! (demo)`;
    // TODO: POST an Backend senden
  });

  console.assert(!!btnReport && !!typeSelect, 'Report controls should exist.');
}
