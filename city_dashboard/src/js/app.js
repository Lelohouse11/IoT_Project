/**
 * @file app.js
 * @description Main entry point for the City Dashboard application.
 * Initializes the map, Grafana integration, and LLM features.
 * Handles the initial application startup sequence.
 */

// App entry: wires up UI scaffolding and feature modules.
import { initMap }    from './map.js';
import { initGrafana } from './grafana.js';
import { initLLM }     from './llm.js';

console.log('app.js v5 loaded');

// Expose initLLM globally for debugging
window.debugInitLLM = initLLM;

/**
 * Starts the application by initializing core components.
 * Delays LLM initialization slightly to ensure the DOM is ready.
 */
function startApp() {
  console.log('Starting App...');
  initMap();
  initGrafana();
  
  // Delay LLM init slightly to ensure DOM is fully settled
  setTimeout(() => {
      console.log('Calling initLLM from app.js...');
      initLLM();
  }, 500);
}

if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', startApp);
} else {
  startApp();
}
