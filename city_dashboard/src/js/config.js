/**
 * @file config.js
 * @description Global configuration settings for the City Dashboard.
 * Contains constants for map settings, API endpoints, polling intervals,
 * LLM configuration, and UI color definitions.
 */

// Global configuration for the City Dashboard

export const CONFIG = {
  // Map settings
  MAP_CENTER: [38.2464, 21.7346],
  MAP_ZOOM: 13,
  
  // API settings
  API_BASE: window.APP_API_BASE || "http://localhost:8000", // e.g. "http://localhost:8000"
  
  // Polling & Data retention
  REFRESH_MS: 30000,           // auto-refresh interval
  PRUNE_MS: 30000,             // prune cadence
  API_WINDOW: '10m',           // lookback for active accidents/traffic
  VIOLATION_WINDOW: '5m',      // lookback for traffic violations
  ACCIDENT_TTL_MS: 5 * 60 * 1000, // keep accidents on map this long after last seen
  VIOLATION_TTL_MS: 5 * 60 * 1000,

  // LLM settings
  LLM_BACKEND: window.LLM_BACKEND_BASE || 'http://localhost:9090',
  LLM_MODEL: window.LLM_MODEL || 'deepseek-r1:8b',
  
  // Auth settings
  AUTH_LOGIN_URL: '/login.html',
  AUTH_DASHBOARD_URL: '/index.html',
};

export const COLORS = {
  speed: v => (v>=70?'#2ecc71':v>=45?'#f1c40f':v>=25?'#e67e22':'#e74c3c'),
  occupancy: frac => (frac<=0.5?'#2ecc71':frac<=0.8?'#f39c12':'#e74c3c'),
  severityClass: s => (s==='major'?'major':s==='medium'?'medium':'minor'),
  violation: type => ({
    'double-parking': '#e67e22',
    'red-light': '#e74c3c',
    'no-stopping': '#f1c40f',
    'near-intersection': '#3498db'
  }[type] || '#1abc9c')
};

export const VIOLATION_LEGEND_ITEMS = [
  { key: 'double-parking', label: 'Double parking' },
  { key: 'red-light', label: 'Red light' },
  { key: 'no-stopping', label: 'No stopping' },
  { key: 'near-intersection', label: 'Near intersection' }
];
