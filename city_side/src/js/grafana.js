// Minimal helper for the Grafana iframe.
// The embedded panel/dashboard URL is configured in index.html.
// We expose a manual refresh to reload the iframe without a full page reload.
export function initGrafana() {
  const btn = document.getElementById('refreshGrafana');
  const iframes = document.querySelectorAll('.grafana-embed');
  
  btn?.addEventListener('click', () => { 
    iframes.forEach(iframe => {
      iframe.src = iframe.src; 
    });
  });
}

export function updateGrafanaTime(startMs, endMs) {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.set('from', startMs);
    url.searchParams.set('to', endMs);
    iframe.src = url.toString();
  });
}

export function resetGrafanaTime() {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.delete('from');
    url.searchParams.delete('to');
    iframe.src = url.toString();
  });
}
