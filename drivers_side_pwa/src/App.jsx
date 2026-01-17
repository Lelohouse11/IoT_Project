import { useEffect, useState } from 'react'
import './App.css'
import BottomNav from './components/BottomNav'
import Header from './components/Header'
import MapView from './components/MapView'
import ProfileMenu from './components/ProfileMenu'
import ReportPanel from './components/ReportPanel'
import RewardsPanel from './components/RewardsPanel'

function App() {
  const [profileOpen, setProfileOpen] = useState(false)
  const [signedIn, setSignedIn] = useState(false)
  const [activeTab, setActiveTab] = useState('map')

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

  return (
    <>
      <Header profileOpen={profileOpen} onToggleProfile={toggleProfile} />
      <ProfileMenu
        signedIn={signedIn}
        open={profileOpen}
        onToggleSignIn={() => setSignedIn((v) => !v)}
        onClose={() => setProfileOpen(false)}
      />
      <main className="wrap">
        <MapView active={activeTab === 'map'} />
        <RewardsPanel active={activeTab === 'rewards'} />
        <ReportPanel active={activeTab === 'report'} />
      </main>
      <BottomNav activeTab={activeTab} onNavigate={setActiveTab} />
    </>
  )
}

export default App
