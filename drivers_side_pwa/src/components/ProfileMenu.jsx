function ProfileMenu({ signedIn, open, onToggleSignIn, onClose }) {
  return (
    <div className={`profile-menu ${open ? 'open' : ''}`} id="profileMenu" role="menu" aria-labelledby="profileBtn">
      <div className="profile-row">
        <div className="avatar" style={{ width: '28px', height: '28px', border: '1px solid rgba(79,209,197,.35)' }}></div>
        <div>
          <div>Driver</div>
          <small>{signedIn ? 'Signed in' : 'Signed out'}</small>
        </div>
      </div>
      <div className="profile-actions">
        <button
          className="btn"
          onClick={() => {
            onToggleSignIn()
            onClose()
          }}
        >
          {signedIn ? 'Sign out' : 'Sign in'}
        </button>
      </div>
    </div>
  )
}

export default ProfileMenu
