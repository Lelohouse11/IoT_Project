import { useEffect, useState } from 'react'
import { fetchUserRewards, fetchRewardsCatalog, redeemRewards } from '../api/rewards'

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
  const [catalog, setCatalog] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [redeeming, setRedeeming] = useState(null)
  const [redeemMessage, setRedeemMessage] = useState('')

  // Fetch reward data and catalog on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        setError(null)
        const [rewardsData, catalogData] = await Promise.all([
          fetchUserRewards(driverId),
          fetchRewardsCatalog()
        ])
        setRewards(rewardsData)
        setCatalog(catalogData)
      } catch (err) {
        setError(err.message || 'Failed to load rewards')
        console.error('Error fetching rewards:', err)
      } finally {
        setLoading(false)
      }
    }

    if (active) {
      loadData()
    }
  }, [active, driverId])

  const handleRedeemReward = async (rewardId, rewardName, pointsCost) => {
    if (rewards.current_points < pointsCost) {
      setRedeemMessage(`Not enough points. You have ${rewards.current_points} pts.`)
      setTimeout(() => setRedeemMessage(''), 3000)
      return
    }

    try {
      setRedeeming(rewardId)
      const result = await redeemRewards(driverId, rewardId)
      
      // Update points locally
      setRewards(prev => ({
        ...prev,
        current_points: result.remaining_points
      }))
      
      setRedeemMessage(result.message || `Successfully redeemed ${rewardName}!`)
      
      // Clear message after 3 seconds
      setTimeout(() => setRedeemMessage(''), 3000)
    } catch (err) {
      setRedeemMessage(`Error: ${err.message}`)
      console.error('Error redeeming reward:', err)
      setTimeout(() => setRedeemMessage(''), 3000)
    } finally {
      setRedeeming(null)
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
                    backgroundColor: redeemMessage.startsWith('Error') || redeemMessage.startsWith('Not enough') ? '#ffebee' : '#e8f5e9',
                    color: redeemMessage.startsWith('Error') || redeemMessage.startsWith('Not enough') ? '#d32f2f' : '#2e7d32',
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
        </div>
      </article>

      {!loading && !error && catalog.length > 0 && (
        <article className="card" style={{ marginTop: '1rem' }}>
          <h2>Available Rewards</h2>
          <div className="body">
            <div style={{ display: 'grid', gap: '1rem' }}>
              {catalog.map((reward) => {
                const canAfford = rewards.current_points >= reward.points_cost
                const isRedeeming = redeeming === reward.id

                return (
                  <div
                    key={reward.id}
                    style={{
                      border: '2px solid var(--accent)',
                      borderRadius: '0.5rem',
                      padding: '1rem',
                      backgroundColor: canAfford ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.1)',
                      boxShadow: canAfford ? '0 2px 8px rgba(0, 0, 0, 0.1)' : 'none'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600' }}>{reward.name}</h3>
                      <span
                        style={{
                          fontWeight: '700',
                          color: canAfford ? 'var(--accent)' : '#999',
                          fontSize: '1rem',
                          whiteSpace: 'nowrap',
                          marginLeft: '0.5rem'
                        }}
                      >
                        {reward.points_cost} pts
                      </span>
                    </div>
                    <p style={{ margin: '0 0 1rem 0', color: '#666', fontSize: '0.9rem' }}>
                      {reward.description}
                    </p>
                    <button
                      className="btn"
                      onClick={() => handleRedeemReward(reward.id, reward.name, reward.points_cost)}
                      disabled={!canAfford || isRedeeming}
                      style={{
                        opacity: !canAfford || isRedeeming ? 0.5 : 1,
                        cursor: !canAfford || isRedeeming ? 'not-allowed' : 'pointer',
                        width: '100%'
                      }}
                    >
                      {isRedeeming ? 'Redeeming...' : canAfford ? 'Redeem' : 'Not Enough Points'}
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        </article>
      )}
    </section>
  )
}

export default RewardsPanel
