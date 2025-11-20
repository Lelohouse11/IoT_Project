// App entry: wires up UI scaffolding and feature modules.
// Order matters a bit: auth (profile state) and drawer (navigation) are light,
// map bootstraps Leaflet + polling, grafana handles iframe refresh, llm is demo.
import { initDrawer } from './drawer.js';
import { initAuth }   from './auth.js';
import { initMap }    from './map.js';
import { initGrafana } from './grafana.js';
import { initLLM }     from './llm.js';

window.addEventListener('DOMContentLoaded', () => {
  initDrawer();
  initAuth();
  initMap();
  initGrafana();
  initLLM();
});
