import { useState } from 'react'
import { getDriverName, getDriverEmail, logout, deleteAccount } from '../services/auth'

function ProfileMenu({ open, onLogout, onClose }) {
  const driverName = getDriverName()
  const driverEmail = getDriverEmail()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  const handleLogout = () => {
    logout()
    onLogout()
    onClose()
  }

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return
    }

    try {
      setIsDeleting(true)
      setDeleteError('')
      await deleteAccount()
      // Account deleted successfully, logout and redirect
      logout()
      onLogout()
      onClose()
    } catch (err) {
      // If session expired, still logout the user
      if (err.message === 'Session expired') {
        logout()
        onLogout()
        onClose()
      } else {
        setDeleteError(err.message || 'Failed to delete account')
        console.error('Error deleting account:', err)
      }
    } finally {
      setIsDeleting(false)
    }
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
        <button
          className="btn btn-danger"
          onClick={handleDeleteAccount}
          disabled={isDeleting}
          style={{backgroundColor: '#dc3545', borderColor: '#dc3545' }}
        >
          {isDeleting ? 'Deleting...' : 'Delete Account'}
        </button>
        {deleteError && (
          <div style={{ color: '#dc3545', fontSize: '0.8rem', marginTop: '0.5rem' }}>
            {deleteError}
          </div>
        )}
      </div>
    </div>
  )
}

export default ProfileMenu
