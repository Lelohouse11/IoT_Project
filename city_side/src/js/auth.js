// Very small in-memory auth mock used to toggle profile UI and handle logout redirect.
const SIGNED_IN_KEY = 'city_side_signed_in';
let signedIn = localStorage.getItem(SIGNED_IN_KEY) === 'true';

export function initAuth() {
  const authBtn       = document.getElementById('authBtn');
  const profileMenu   = document.getElementById('profileMenu');
  const authToggleBtn = document.getElementById('authToggleBtn');
  const profileName   = document.getElementById('profileName');
  const profileStatus = document.getElementById('profileStatus');

  // If a protected page is accessed without a session, send to login.
  if (!signedIn) {
    window.location.href = '/public/login.html';
    return;
  }

  function renderProfile() {
    profileName.textContent   = 'City Admin';
    profileStatus.textContent = 'Signed in';
    authToggleBtn.textContent = 'Sign out';
  }

  function toggleProfileMenu(open) {
    profileMenu.classList.toggle('open', open ?? !profileMenu.classList.contains('open'));
  }

  authBtn.addEventListener('click', (e) => { e.stopPropagation(); toggleProfileMenu(); });
  document.addEventListener('click', (e) => {
    if (!profileMenu.contains(e.target) && e.target !== authBtn) profileMenu.classList.remove('open');
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') profileMenu.classList.remove('open'); });

  authToggleBtn.addEventListener('click', () => {
    signedIn = false;
    localStorage.setItem(SIGNED_IN_KEY, 'false');
    toggleProfileMenu(false);
    window.location.href = '/public/login.html';
  });

  renderProfile();
}

// Read-only accessor for other modules (e.g., llm.js)
export function isSignedIn() { return signedIn; }
