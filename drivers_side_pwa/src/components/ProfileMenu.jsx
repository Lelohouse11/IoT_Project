import { getDriverName, getDriverEmail, logout } from '../services/auth'

function ProfileMenu({ open, onLogout, onClose }) {
  const driverName = getDriverName()
  const driverEmail = getDriverEmail()

  const handleLogout = () => {
    logout()
    onLogout()
    onClose()
  }

  return (
    <div className={`profile-menu ${open ? 'open' : ''}`} id="profileMenu" role="menu" aria-labelledby="profileBtn">
      <div className="profile-row">
        <div className="avatar" style={{ width: '28px', height: '28px', border: '1px solid rgba(79,209,197,.35)' }}></div>
        <div>
          <div>{driverName}</div>
          <small>{driverEmail}</small>
        </div>
      </div>
      <div className="profile-actions">
        <button
          className="btn"
          onClick={handleLogout}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}

export default ProfileMenu
