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
