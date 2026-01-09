function RewardsPanel({ active, points, onRedeem }) {
  return (
    <section className={`view ${active ? 'active' : ''}`} aria-hidden={!active} id="rewards-card">
      <article className="card">
        <h2>Rewards</h2>
        <div className="body">
          <div className="reward-points">{points.toLocaleString()} pts</div>
          <ul className="clean">
            <li>No speeding: 7-day streak</li>
            <li>No double parking: 7-day streak</li>
          </ul>
          <div style={{ height: '.75rem' }}></div>
          <div className="controls">
            <button className="btn" onClick={onRedeem}>Redeem Rewards</button>
          </div>
        </div>
      </article>
    </section>
  )
}

export default RewardsPanel
