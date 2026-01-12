import { useEffect, useState } from 'react'
import { fetchUserRewards, redeemRewards } from '../api/rewards'

function StreakProgressBar({ streakDays, streakType, progressPct }) {
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <span style={{ fontWeight: '600', textTransform: 'capitalize' }}>{streakType} Streak</span>
        <span style={{ fontSize: '0.9rem', color: 'var(--accent)' }}>{streakDays} days</span>
      </div>
      <div
        style={{
          backgroundColor: '#e0e0e0',
          borderRadius: '0.25rem',
          height: '0.75rem',
          overflow: 'hidden'
        }}
      >
        <div
          style={{
            backgroundColor: 'var(--accent)',
            height: '100%',
            width: `${progressPct}%`,
            transition: 'width 0.3s ease'
          }}
        />
      </div>
      <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem', textAlign: 'right' }}>
        {progressPct}% to next 30-day milestone
      </div>
    </div>
  )
}

function RewardsPanel({ active }) {
  // TODO: Replace hardcoded driver_id=1 with user ID extracted from auth token
  // when user management is implemented:
  // const driverId = getUserIdFromToken() or similar
  const driverId = 1

  const [rewards, setRewards] = useState({
    current_points: 0,
    traffic_streak_days: 0,
    parking_streak_days: 0,
    traffic_progress_pct: 0,
    parking_progress_pct: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [redeemingPoints, setRedeemingPoints] = useState(null)
  const [redeemMessage, setRedeemMessage] = useState('')

  // Fetch reward data on component mount
  useEffect(() => {
    const loadRewards = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchUserRewards(driverId)
        setRewards(data)
      } catch (err) {
        setError(err.message || 'Failed to load rewards')
        console.error('Error fetching rewards:', err)
      } finally {
        setLoading(false)
      }
    }

    if (active) {
      loadRewards()
    }
  }, [active, driverId])

  const handleRedeem = async () => {
    // For now, just deduct 250 points (dummy redemption)
    const pointsToRedeem = 250
    
    if (rewards.current_points < pointsToRedeem) {
      setRedeemMessage(`Not enough points. You have ${rewards.current_points} pts.`)
      return
    }

    try {
      setRedeemingPoints(true)
      const updated = await redeemRewards(driverId, pointsToRedeem)
      setRewards(updated)
      setRedeemMessage(`Successfully redeemed ${pointsToRedeem} points!`)
      
      // Clear message after 3 seconds
      setTimeout(() => setRedeemMessage(''), 3000)
    } catch (err) {
      setRedeemMessage(`Error: ${err.message}`)
      console.error('Error redeeming rewards:', err)
    } finally {
      setRedeemingPoints(false)
    }
  }

  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="rewards-card">
      <article className="card">
        <h2>Rewards</h2>
        <div className="body">
          {loading && <div style={{ textAlign: 'center', color: '#666' }}>Loading rewards...</div>}

          {error && (
            <div style={{ color: '#d32f2f', marginBottom: '1rem', textAlign: 'center' }}>
              Error: {error}
            </div>
          )}

          {!loading && !error && (
            <>
              <div className="reward-points" style={{ marginBottom: '1.5rem' }}>
                {rewards.current_points.toLocaleString()} pts
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <StreakProgressBar
                  streakDays={rewards.traffic_streak_days}
                  streakType="Traffic"
                  progressPct={rewards.traffic_progress_pct}
                />
                <StreakProgressBar
                  streakDays={rewards.parking_streak_days}
                  streakType="Parking"
                  progressPct={rewards.parking_progress_pct}
                />
              </div>

              {redeemMessage && (
                <div
                  style={{
                    marginBottom: '1rem',
                    padding: '0.75rem',
                    backgroundColor: redeemMessage.startsWith('Error') ? '#ffebee' : '#e8f5e9',
                    color: redeemMessage.startsWith('Error') ? '#d32f2f' : '#2e7d32',
                    borderRadius: '0.25rem',
                    fontSize: '0.9rem',
                    textAlign: 'center'
                  }}
                >
                  {redeemMessage}
                </div>
              )}
            </>
          )}

          <div style={{ height: '.75rem' }}></div>
          <div className="controls">
            <button
              className="btn"
              onClick={handleRedeem}
              disabled={loading || redeemingPoints}
              style={{ opacity: loading || redeemingPoints ? 0.6 : 1 }}
            >
              {redeemingPoints ? 'Redeeming...' : 'Redeem Rewards'}
            </button>
          </div>
        </div>
      </article>
    </section>
  )
}

export default RewardsPanel
