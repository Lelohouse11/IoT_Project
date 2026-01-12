const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')
const REWARD_API_BASE = 'http://localhost:8000' // Reward endpoints run on port 8000 (map_service.py)

/**
 * Fetch reward data for a driver from the backend.
 * 
 * TODO: Replace hardcoded driver_id with user ID extracted from auth token
 * when user management is implemented.
 * 
 * @param {number} driverId - The driver ID from driver_profiles table
 * @returns {Promise<Object>} Reward data with current_points, streaks, and milestone progress
 * @throws {Error} If the API request fails
 */
export async function fetchUserRewards(driverId) {
  const url = `${REWARD_API_BASE}/api/rewards/${driverId}`.replace(/^\/+api/, '/api')
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  
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
  const url = `${REWARD_API_BASE}/api/rewards/catalog`.replace(/^\/+api/, '/api')
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  
  if (!res.ok) {
    throw new Error(`Failed to fetch rewards catalog (${res.status})`)
  }

  const data = await res.json()
  return data
}

/**
 * Redeem a specific reward for a driver.
 * 
 * @param {number} driverId - The driver ID
 * @param {number} rewardId - The ID of the reward to redeem
 * @returns {Promise<Object>} Result with success status, message, and remaining points
 * @throws {Error} If the API request fails or user has insufficient points
 */
export async function redeemRewards(driverId, rewardId) {
  const url = `${REWARD_API_BASE}/api/rewards/${driverId}/redeem`.replace(/^\/+api/, '/api')
  
  const res = await fetch(url, {
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
