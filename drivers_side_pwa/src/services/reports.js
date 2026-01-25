/**
 * Reports service for submitting accident and traffic violation reports
 */

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

/**
 * Submit an accident or traffic violation report
 * 
 * @param {number} latitude - Report location latitude
 * @param {number} longitude - Report location longitude
 * @param {string} severity - Report severity ('minor', 'medium', 'major')
 * @param {string} description - Report description
 * @returns {Promise<Object>} Server response with report ID and confirmation
 * @throws {Error} If the API request fails
 */
export async function submitReport({ latitude, longitude, severity, description }) {
  const url = `${API_BASE}/pwa/reports`.replace(/^\/+pwa/, '/pwa')
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      latitude,
      longitude,
      severity,
      description
    })
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Server error: ${response.status}`)
  }

  return await response.json()
}
