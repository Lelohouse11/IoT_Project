/**
 * Placeholder page for reward redemption.
 * 
 * This is a mock rewards catalog page linked from the RewardsPanel "Redeem Rewards" button.
 * In the future, this will display actual available rewards that drivers can claim
 * with their accumulated points.
 * 
 * TODO: Implement actual reward catalog with:
 * - Reward items with point costs
 * - Purchase/redemption flow
 * - Redemption history
 * - Integration with reward_router.py POST /api/rewards/{driver_id}/redeem
 */

function RedeemPage() {
  const handleGoBack = () => {
    window.history.back()
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <button
        onClick={handleGoBack}
        style={{
          marginBottom: '2rem',
          padding: '0.5rem 1rem',
          backgroundColor: '#f0f0f0',
          border: '1px solid #ddd',
          borderRadius: '0.25rem',
          cursor: 'pointer',
          fontSize: '0.9rem'
        }}
      >
        ← Back
      </button>

      <h1 style={{ marginBottom: '1rem' }}>Redeem Your Rewards</h1>

      <div
        style={{
          backgroundColor: '#fff3e0',
          border: '1px solid #ffe0b2',
          borderRadius: '0.5rem',
          padding: '1.5rem',
          marginBottom: '2rem',
          textAlign: 'center'
        }}
      >
        <p style={{ margin: '0', fontSize: '1.1rem', fontWeight: '600' }}>Coming Soon</p>
        <p style={{ margin: '0.5rem 0 0 0', color: '#666', fontSize: '0.95rem' }}>
          Reward catalog is under development. More rewards will be available soon!
        </p>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Placeholder Rewards</h2>
        <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '1rem' }}>
          These are examples of rewards that will be available:
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: '1rem'
          }}
        >
          {[
            { name: 'Discount Voucher', points: 250, description: 'Parking discount voucher' },
            { name: 'Priority Parking', points: 500, description: '1 month of priority parking' },
            { name: 'Insurance Discount', points: 1000, description: '10% insurance discount' }
          ].map((reward) => (
            <div
              key={reward.name}
              style={{
                border: '1px solid #ddd',
                borderRadius: '0.5rem',
                padding: '1rem',
                opacity: 0.6,
                cursor: 'not-allowed'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: '600' }}>{reward.name}</span>
                <span style={{ color: 'var(--accent)', fontWeight: '600' }}>{reward.points} pts</span>
              </div>
              <p style={{ margin: '0', fontSize: '0.9rem', color: '#666' }}>
                {reward.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div style={{ fontSize: '0.9rem', color: '#999', textAlign: 'center', marginTop: '2rem' }}>
        <p>Rewards catalog will be integrated when the backend implementation is complete.</p>
      </div>
    </div>
  )
}

export default RedeemPage
