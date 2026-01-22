import { useEffect, useState } from 'react'
import './App.css'
import BottomNav from './components/BottomNav'
import Header from './components/Header'
import MapView from './components/MapView'
import ProfileMenu from './components/ProfileMenu'
import ReportPanel from './components/ReportPanel'
import RewardsPanel from './components/RewardsPanel'
import Login from './pages/Login'
import Register from './pages/Register'
import { isAuthenticated, refreshToken } from './utils/auth'

function App() {
  const [authView, setAuthView] = useState('login') // 'login' | 'register' | 'authenticated'
  const [profileOpen, setProfileOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('map')

  // Check authentication on mount
  useEffect(() => {
    if (isAuthenticated()) {
      setAuthView('authenticated')
    } else {
      setAuthView('login')
    }
  }, [])

  // Set up token refresh interval (every 15 minutes)
  useEffect(() => {
    if (authView !== 'authenticated') {
      return
    }

    const refreshInterval = setInterval(async () => {
      const refreshed = await refreshToken()
      if (!refreshed) {
        // Token refresh failed, logout
        setAuthView('login')
      }
    }, 15 * 60 * 1000) // 15 minutes

    return () => clearInterval(refreshInterval)
  }, [authView])

  useEffect(() => {
    const onClick = (e) => {
      if (profileOpen) {
        const menu = document.getElementById('profileMenu')
        const button = document.getElementById('profileBtn')
        if (menu && !menu.contains(e.target) && button && !button.contains(e.target)) {
          setProfileOpen(false)
        }
      }
    }
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setProfileOpen(false)
      }
    }
    document.addEventListener('click', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('click', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [profileOpen])

  const toggleProfile = () => setProfileOpen((v) => !v)

  const handleLoginSuccess = () => {
    setAuthView('authenticated')
  }

  const handleLogout = () => {
    setAuthView('login')
    setProfileOpen(false)
  }

  // Show login or register page if not authenticated
  if (authView === 'login') {
    return <Login onLoginSuccess={handleLoginSuccess} onSwitchToRegister={() => setAuthView('register')} />
  }

  if (authView === 'register') {
    return <Register onRegisterSuccess={handleLoginSuccess} onSwitchToLogin={() => setAuthView('login')} />
  }

  // Show main app if authenticated
  return (
    <>
      <Header profileOpen={profileOpen} onToggleProfile={toggleProfile} />
      <ProfileMenu
        open={profileOpen}
        onLogout={handleLogout}
        onClose={() => setProfileOpen(false)}
      />
      <main className="wrap">
        <MapView active={activeTab === 'map'} />
        <RewardsPanel active={activeTab === 'rewards'} onSessionExpired={handleLogout} />
        <ReportPanel
          active={activeTab === 'report'}
          reportType={reportType}
          onReportTypeChange={setReportType}
          onSendReport={handleReport}
          reportMsg={reportMsg}
        />
      </main>
      <BottomNav activeTab={activeTab} onNavigate={setActiveTab} />
    </>
  )
}

export default App
