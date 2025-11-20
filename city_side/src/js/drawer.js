// Lightweight drawer (side menu) controller with ARIA updates for accessibility.
export function initDrawer() {
  const drawer = document.getElementById('drawer');
  const burger = document.getElementById('burger');
  const scrim  = document.getElementById('scrim');

  function setDrawer(open) {
    drawer.classList.toggle('open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    burger.setAttribute('aria-expanded', String(open));
  }

  burger.addEventListener('click', () => setDrawer(!drawer.classList.contains('open')));
  scrim.addEventListener('click', () => setDrawer(false));
}
