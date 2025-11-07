export function initGrafana() {
  const btn = document.getElementById('refreshGrafana');
  const iframe = document.getElementById('grafanaFrame');
  btn?.addEventListener('click', () => { iframe.src = iframe.src; });
  // Optional: Parameter/Time-Range per URL steuern
}
