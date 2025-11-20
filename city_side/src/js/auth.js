// Very small in-memory auth mock used to toggle profile UI and demo flows.
let signedIn = false;

export function initAuth() {
  const authBtn       = document.getElementById('authBtn');
  const profileMenu   = document.getElementById('profileMenu');
  const authToggleBtn = document.getElementById('authToggleBtn');
  const profileName   = document.getElementById('profileName');
  const profileStatus = document.getElementById('profileStatus');

  function renderProfile() {
    profileName.textContent   = signedIn ? 'City Admin' : 'Guest';
    profileStatus.textContent = signedIn ? 'Signed in' : 'Signed out';
    authToggleBtn.textContent = signedIn ? 'Sign out' : 'Sign in';
  }

  function toggleProfileMenu(open) {
    profileMenu.classList.toggle('open', open ?? !profileMenu.classList.contains('open'));
  }

  authBtn.addEventListener('click', (e) => { e.stopPropagation(); toggleProfileMenu(); });
  document.addEventListener('click', (e) => {
    if (!profileMenu.contains(e.target) && e.target !== authBtn) profileMenu.classList.remove('open');
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') profileMenu.classList.remove('open'); });

  authToggleBtn.addEventListener('click', () => { signedIn = !signedIn; renderProfile(); toggleProfileMenu(false); });

  renderProfile();
}

// Read-only accessor for other modules (e.g., llm.js)
export function isSignedIn() { return signedIn; }
