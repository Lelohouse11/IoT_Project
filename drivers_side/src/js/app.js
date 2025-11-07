import { initDrawer }   from './drawer.js';
import { initAuth }     from './auth.js';
import { initMap }      from './map.js';
import { initRewards }  from './rewards.js';
import { initParking }  from './parking.js';
import { initReports }  from './reports.js';
import { initPrefs }    from './prefs.js';

window.addEventListener('DOMContentLoaded', () => {
  initDrawer();
  initAuth();
  const mapApi = initMap();     // gibt optionale Helfer zurück
  initRewards();
  initParking(mapApi);
  initReports();
  initPrefs();
});
