function Header({ profileOpen, onToggleProfile }) {
  return (
    <header className="topbar" role="banner">
      <div className="brand">
        <span className="brand-dot"></span>
        <span>Smart Mobility - Driver</span>
      </div>
      <div className="spacer"></div>
      <button
        id="profileBtn"
        className="avatar"
        title="Profile"
        aria-haspopup="menu"
        aria-expanded={profileOpen}
        onClick={onToggleProfile}
      ></button>
    </header>
  )
}

export default Header
