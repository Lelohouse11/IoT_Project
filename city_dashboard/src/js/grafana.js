/**
 * @file grafana.js
 * @description Helper module for managing Grafana iframe integration.
 * Provides functions to update Grafana dashboards based on time ranges and map locations.
 */

// Minimal helper for the Grafana iframe.
// The embedded panel/dashboard URL is configured in index.html.
// We expose a manual refresh to reload the iframe without a full page reload.

/**
 * Initializes the Grafana refresh button.
 * Adds a click listener to reload all Grafana iframes.
 */
export function initGrafana() {
  const btn = document.getElementById('refreshGrafana');
  
  btn?.addEventListener('click', () => { 
    reloadGrafana();
  });
}

/**
 * Reloads all Grafana iframes by resetting their src attribute.
 */
export function reloadGrafana() {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    iframe.src = iframe.src; 
  });
}

/**
 * Updates the time range for all Grafana iframes.
 * @param {number} startMs - Start time in milliseconds.
 * @param {number} endMs - End time in milliseconds.
 */
export function updateGrafanaTime(startMs, endMs) {
  const iframes = document.querySelectorAll('.grafana-embed');
  iframes.forEach(iframe => {
    const url = new URL(iframe.src);
    url.searchParams.set('from', startMs);
    url.searchParams.set('to', endMs);
    iframe.src = url.toString();
  });
}

/**
 * Updates the location variables for Grafana dashboards.
 * Used to filter data based on the current map view.
 * @param {number} latMin - Minimum latitude.
 * @param {number} latMax - Maximum latitude.
 * @param {number} lngMin - Minimum longitude.
 * @param {number} lngMax - Maximum longitude.
 */
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

/**
 * Resets all Grafana filters (time and location).
 */
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

/**
 * Clears only the location filters from Grafana dashboards.
 */
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
