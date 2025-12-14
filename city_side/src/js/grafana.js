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

export function updateGrafanaLocation(latMin, latMax, lngMin, lngMax) {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.set('var-min_lat', latMin);
    url.searchParams.set('var-max_lat', latMax);
    url.searchParams.set('var-min_lng', lngMin);
    url.searchParams.set('var-max_lng', lngMax);
    iframe.src = url.toString();
  });
}

export function resetGrafanaFilters() {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.delete('from');
    url.searchParams.delete('to');
    url.searchParams.delete('var-min_lat');
    url.searchParams.delete('var-max_lat');
    url.searchParams.delete('var-min_lng');
    url.searchParams.delete('var-max_lng');
    iframe.src = url.toString();
  });
}

export function clearGrafanaLocation() {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.delete('var-min_lat');
    url.searchParams.delete('var-max_lat');
    url.searchParams.delete('var-min_lng');
    url.searchParams.delete('var-max_lng');
    iframe.src = url.toString();
  });
}
