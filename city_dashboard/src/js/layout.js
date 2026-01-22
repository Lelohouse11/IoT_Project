/**
 * @file layout.js
 * @description Manages the common layout elements of the application.
 * Handles the injection of the header, navigation, and profile menu.
 * Also manages the account deletion modal.
 */

import { initAuth } from './auth.js';

/**
 * Initializes the application layout.
 * Injects the header HTML, highlights the active navigation link,
 * and initializes the authentication module.
 */
export function initLayout() {
  const headerHTML = `
  <header class="topbar" role="banner">
    <div class="brand" aria-label="Smart City Admin">
      <span class="brand-dot" aria-hidden="true"></span>
      <a href="/index.html" aria-label="Back to dashboard" style="color: inherit; text-decoration: none;">Smart City - Admin</a>
    </div>
    <nav class="topnav" aria-label="Utility links">
      <a href="/index.html" id="nav-dashboard">Dashboard</a>
      <a href="/help.html" id="nav-help">Help</a>
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
    <div class="profile-actions" style="display:flex; justify-content:space-between; align-items:center;">
      <button class="btn" id="deleteAccountBtn" style="color:#e74c3c; border-color:rgba(231,76,60,0.3); font-size:0.85rem; padding:0.3rem 0.6rem;">Delete</button>
      <button class="btn" id="authToggleBtn">Sign in</button>
    </div>
  </div>

  <!-- Delete Confirmation Modal -->
  <div id="deleteConfirmModal" class="modal-overlay">
    <div class="modal-content">
      <div class="modal-icon warn">!</div>
      <h2 style="margin-top:0; color:var(--text)">Delete Account?</h2>
      <p style="color:var(--muted)">Are you sure you want to delete your account? This action cannot be undone.</p>
      <div style="display:flex; gap:1rem; justify-content:center; margin-top:1.5rem;">
        <button id="cancelDeleteBtn" class="btn" style="border-color:rgba(255,255,255,0.2)">Cancel</button>
        <button id="confirmDeleteBtn" class="btn" style="background:rgba(231,76,60,0.2); color:#e74c3c; border-color:rgba(231,76,60,0.5)">Delete</button>
      </div>
    </div>
  </div>
  `;

  const layoutContainer = document.getElementById('layout-header');
  if (layoutContainer) {
    layoutContainer.innerHTML = headerHTML;
    
    // Highlight active link
    const path = window.location.pathname;
    if (path.includes('index.html')) document.getElementById('nav-dashboard')?.setAttribute('aria-current', 'page');
    if (path.includes('help.html')) document.getElementById('nav-help')?.setAttribute('aria-current', 'page');

    // Initialize auth now that elements exist
    initAuth();
  }
}
