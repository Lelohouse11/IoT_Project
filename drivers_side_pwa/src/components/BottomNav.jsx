function BottomNav({ activeTab, onNavigate }) {
  return (
    <nav className="bottom-nav" aria-label="Schnellnavigation">
      <button
        type="button"
        className={`nav-btn ${activeTab === 'map' ? 'active' : ''}`}
        onClick={() => onNavigate('map')}
        aria-pressed={activeTab === 'map'}
      >
        <span>Map</span>
      </button>
      <button
        type="button"
        className={`nav-btn ${activeTab === 'rewards' ? 'active' : ''}`}
        onClick={() => onNavigate('rewards')}
        aria-pressed={activeTab === 'rewards'}
      >
        <span>Rewards</span>
      </button>
      <button
        type="button"
        className={`nav-btn ${activeTab === 'report' ? 'active' : ''}`}
        onClick={() => onNavigate('report')}
        aria-pressed={activeTab === 'report'}
      >
        <span>Report</span>
      </button>
    </nav>
  )
}

export default BottomNav
