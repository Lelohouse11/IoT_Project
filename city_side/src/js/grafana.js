// Minimal helper for the Grafana iframe.
// The embedded panel/dashboard URL is configured in index.html.
// We expose a manual refresh to reload the iframe without a full page reload.
export function initGrafana() {
  const btn = document.getElementById('refreshGrafana');
  const iframe = document.getElementById('grafanaFrame');
  btn?.addEventListener('click', () => { iframe.src = iframe.src; });
  // Optional: control parameters/time range via the iframe src URL (not handled here).
}
