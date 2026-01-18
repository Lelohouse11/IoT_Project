/**
 * @file auth.js
 * @description Handles client-side authentication logic for the City Dashboard.
 * Manages user session state, profile UI toggling, and logout functionality.
 * Includes a mock auth implementation for demonstration purposes.
 */

// Very small in-memory auth mock used to toggle profile UI and handle logout redirect.
import { CONFIG } from './config.js';

const SIGNED_IN_KEY = 'city_side_signed_in';
let signedIn = localStorage.getItem(SIGNED_IN_KEY) === 'true';

/**
 * Initializes the authentication module.
 * Sets up event listeners for the profile menu, sign-out, and account deletion.
 * Redirects to the login page if the user is not signed in.
 */
export function initAuth() {
  const authBtn       = document.getElementById('authBtn');
  const profileMenu   = document.getElementById('profileMenu');
  const authToggleBtn = document.getElementById('authToggleBtn');
  const deleteAccountBtn = document.getElementById('deleteAccountBtn');
  const profileName   = document.getElementById('profileName');
  const profileStatus = document.getElementById('profileStatus');

  // If a protected page is accessed without a session, send to login.
  if (!signedIn) {
    window.location.href = CONFIG.AUTH_LOGIN_URL;
    return;
  }

  function renderProfile() {
    const name = localStorage.getItem('user_name') || 'City Admin';
    const email = localStorage.getItem('user_email') || 'Signed in';
    
    profileName.textContent   = name;
    profileStatus.textContent = email;
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
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_email');
    localStorage.removeItem('access_token');
    toggleProfileMenu(false);
    window.location.href = CONFIG.AUTH_LOGIN_URL;
  });

  if (deleteAccountBtn) {
    const deleteConfirmModal = document.getElementById('deleteConfirmModal');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    deleteAccountBtn.addEventListener('click', () => {
      toggleProfileMenu(false);
      if (deleteConfirmModal) deleteConfirmModal.classList.add('show');
    });

    if (cancelDeleteBtn) {
      cancelDeleteBtn.addEventListener('click', () => {
        deleteConfirmModal.classList.remove('show');
      });
    }

    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener('click', async () => {
        confirmDeleteBtn.disabled = true;
        confirmDeleteBtn.textContent = 'Deleting...';

        const token = localStorage.getItem('access_token');
        try {
          const response = await fetch('http://localhost:8002/delete_account', {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (response.ok) {
            authToggleBtn.click();
          } else {
            alert('Failed to delete account.');
            confirmDeleteBtn.disabled = false;
            confirmDeleteBtn.textContent = 'Delete';
          }
        } catch (error) {
          console.error('Error deleting account:', error);
          alert('An error occurred.');
          confirmDeleteBtn.disabled = false;
          confirmDeleteBtn.textContent = 'Delete';
        }
      });
    }

    if (deleteConfirmModal) {
      deleteConfirmModal.addEventListener('click', (e) => {
        if (e.target === deleteConfirmModal) deleteConfirmModal.classList.remove('show');
      });
    }
  }

  renderProfile();
}

// Read-only accessor for other modules (e.g., llm.js)
export function isSignedIn() { return signedIn; }
