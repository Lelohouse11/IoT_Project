import { authenticatedFetch, getDriverId } from './auth'

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

/**
 * Fetch reward data for the authenticated driver from the backend.
 * 
 * @returns {Promise<Object>} Reward data with current_points, streaks, and milestone progress
 * @throws {Error} If the API request fails or user is not authenticated
 */
export async function fetchUserRewards() {
  const driverId = getDriverId()
  
  if (!driverId) {
    throw new Error('Not authenticated')
  }

  const url = `${API_BASE}/api/rewards/${driverId}`.replace(/^\/+api/, '/api')
  const res = await authenticatedFetch(url, { headers: { Accept: 'application/json' } })
  
  if (!res.ok) {
    throw new Error(`Failed to fetch rewards (${res.status})`)
  }

  const data = await res.json()
  
  // Ensure numeric fields are properly parsed
  return {
    current_points: parseInt(data.current_points, 10) || 0,
    traffic_streak_days: parseInt(data.traffic_streak_days, 10) || 0,
    parking_streak_days: parseInt(data.parking_streak_days, 10) || 0,
    traffic_progress_pct: parseInt(data.traffic_progress_pct, 10) || 0,
    parking_progress_pct: parseInt(data.parking_progress_pct, 10) || 0
  }
}

/**
 * Fetch available rewards from the catalog.
 * 
 * @returns {Promise<Array>} List of available rewards with id, name, description, points_cost, category
 * @throws {Error} If the API request fails
 */
export async function fetchRewardsCatalog() {
  const url = `${API_BASE}/api/rewards/catalog`.replace(/^\/+api/, '/api')
  const res = await authenticatedFetch(url, { headers: { Accept: 'application/json' } })
  
  if (!res.ok) {
    throw new Error(`Failed to fetch rewards catalog (${res.status})`)
  }

  const data = await res.json()
  return data
}

/**
 * Redeem a specific reward for the authenticated driver.
 * 
 * @param {number} rewardId - The ID of the reward to redeem
 * @returns {Promise<Object>} Result with success status, message, and remaining points
 * @throws {Error} If the API request fails or user has insufficient points
 */
export async function redeemRewards(rewardId) {
  const driverId = getDriverId()
  
  if (!driverId) {
    throw new Error('Not authenticated')
  }

  const url = `${API_BASE}/api/rewards/${driverId}/redeem`.replace(/^\/+api/, '/api')
  
  const res = await authenticatedFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: JSON.stringify({ reward_id: rewardId })
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Redemption failed (${res.status})`)
  }

  const data = await res.json()
  return data
}
