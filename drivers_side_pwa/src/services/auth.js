/**
 * Auth utility module for driver authentication
 * Handles token management, login, logout, and token refresh
 */

// Use environment variable or relative URL for flexibility
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  const token = localStorage.getItem('driver_token');
  return !!token;
}

/**
 * Get the current driver's ID from localStorage
 */
export function getDriverId() {
  const driverId = localStorage.getItem('driver_id');
  return driverId ? parseInt(driverId, 10) : null;
}

/**
 * Get the current driver's name
 */
export function getDriverName() {
  return localStorage.getItem('driver_name') || 'Driver';
}

/**
 * Get the current driver's email
 */
export function getDriverEmail() {
  return localStorage.getItem('driver_email') || '';
}

/**
 * Get the current driver's license plate
 */
export function getDriverLicensePlate() {
  return localStorage.getItem('driver_license_plate') || '';
}

/**
 * Get the authentication token
 */
export function getToken() {
  return localStorage.getItem('driver_token');
}

/**
 * Logout the current user
 */
export function logout() {
  localStorage.removeItem('driver_token');
  localStorage.removeItem('driver_name');
  localStorage.removeItem('driver_email');
  localStorage.removeItem('driver_id');
  localStorage.removeItem('driver_license_plate');
}

/**
 * Refresh the authentication token
 * Returns the new token data or null if refresh failed
 */
export async function refreshToken() {
  const token = getToken();
  
  if (!token) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE}/public/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      
      // Update localStorage with new token and data
      localStorage.setItem('driver_token', data.access_token);
      localStorage.setItem('driver_name', data.username);
      localStorage.setItem('driver_email', data.email);
      localStorage.setItem('driver_id', data.driver_id);
      
      return data;
    } else {
      // Token refresh failed, clear auth data
      logout();
      return null;
    }
  } catch (error) {
    console.error('Token refresh error:', error);
    return null;
  }
}

/**
 * Make an authenticated API request
 * Automatically includes the Authorization header
 */
export async function authenticatedFetch(url, options = {}) {
  const token = getToken();
  
  if (!token) {
    throw new Error('Not authenticated');
  }

  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // If we get a 401, try to refresh the token once
  if (response.status === 401) {
    const refreshed = await refreshToken();
    
    if (refreshed) {
      // Retry the request with the new token
      headers.Authorization = `Bearer ${refreshed.access_token}`;
      return fetch(url, {
        ...options,
        headers,
      });
    } else {
      // Refresh failed, user needs to login again
      throw new Error('Session expired');
    }
  }

  return response;
}

/**
 * Delete the current driver's account
 * @throws {Error} If the request fails or user is not authenticated
 */
export async function deleteAccount() {
  const token = getToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE}/public/account`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to delete account (${response.status})`);
    }
  } catch (error) {
    console.error('Delete account error:', error);
    throw error;
  }
}
