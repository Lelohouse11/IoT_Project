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
 * Redeem rewards for a driver.
 * 
 * TODO: Add proper error handling and user feedback when redemption is implemented.
 * 
 * @param {number} driverId - The driver ID
 * @param {number} pointsToRedeem - Number of points to redeem
 * @returns {Promise<Object>} Updated reward data after redemption
 * @throws {Error} If the API request fails or user has insufficient points
 */
export async function redeemRewards(driverId, pointsToRedeem) {
  const url = `${REWARD_API_BASE}/api/rewards/${driverId}/redeem`.replace(/^\/+api/, '/api')
  
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json'
    },
    body: JSON.stringify({ points_to_redeem: pointsToRedeem })
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `Redemption failed (${res.status})`)
  }

  const data = await res.json()
  
  // Extract and parse the updated rewards from the response
  const rewards = data.rewards || {}
  return {
    current_points: parseInt(rewards.current_points, 10) || 0,
    traffic_streak_days: parseInt(rewards.traffic_streak_days, 10) || 0,
    parking_streak_days: parseInt(rewards.parking_streak_days, 10) || 0,
    traffic_progress_pct: parseInt(rewards.traffic_progress_pct, 10) || 0,
    parking_progress_pct: parseInt(rewards.parking_progress_pct, 10) || 0
  }
}
