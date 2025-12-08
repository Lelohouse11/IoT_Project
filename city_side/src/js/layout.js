import { initAuth } from './auth.js';

export function initLayout() {
  const headerHTML = `
  <header class="topbar" role="banner">
    <div class="brand" aria-label="Smart City Admin">
      <span class="brand-dot" aria-hidden="true"></span>
      <a href="/public/index.html" aria-label="Back to dashboard" style="color: inherit; text-decoration: none;">Smart City - Admin</a>
    </div>
    <nav class="topnav" aria-label="Utility links">
      <a href="/public/index.html" id="nav-dashboard">Dashboard</a>
      <a href="/public/settings.html" id="nav-settings">Settings</a>
      <a href="/public/help.html" id="nav-help">Help</a>
    </nav>
    <div class="spacer"></div>
    <button
      id="authBtn"
      class="avatar"
      title="Sign in / Sign out"
      aria-haspopup="menu"
      aria-expanded="false"
    ></button>
  </header>

  <div class="profile-menu" id="profileMenu" role="menu" aria-labelledby="authBtn">
    <div class="profile-row">
      <div
        class="avatar"
        style="width:28px;height:28px;border:1px solid rgba(79,209,197,.35)"
      ></div>
      <div>
        <div id="profileName">Guest</div>
        <small id="profileStatus">Signed out</small>
      </div>
    </div>
    <div class="profile-actions">
      <button class="btn" id="authToggleBtn">Sign in</button>
    </div>
  </div>
  `;

  const layoutContainer = document.getElementById('layout-header');
  if (layoutContainer) {
    layoutContainer.innerHTML = headerHTML;
    
    // Highlight active link
    const path = window.location.pathname;
    if (path.includes('index.html')) document.getElementById('nav-dashboard')?.setAttribute('aria-current', 'page');
    if (path.includes('settings.html')) document.getElementById('nav-settings')?.setAttribute('aria-current', 'page');
    if (path.includes('help.html')) document.getElementById('nav-help')?.setAttribute('aria-current', 'page');

    // Initialize auth now that elements exist
    initAuth();
  }
}
