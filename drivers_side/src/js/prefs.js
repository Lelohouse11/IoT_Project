export function initPrefs() {
  const prefAvoidNarrow  = document.getElementById('prefAvoidNarrow');
  const prefAvoidRisk    = document.getElementById('prefAvoidRisk');
  const prefAvoidTraffic = document.getElementById('prefAvoidTraffic');

  [prefAvoidNarrow, prefAvoidRisk, prefAvoidTraffic].forEach(el => {
    el?.addEventListener('change', () => {
      console.log('Preference changed', el.id, el.checked);
      // TODO: an Backend senden / Routing-Profile anpassen
    });
  });

  console.assert(!!prefAvoidNarrow && !!prefAvoidRisk && !!prefAvoidTraffic, 'Preference checkboxes should exist.');
}
