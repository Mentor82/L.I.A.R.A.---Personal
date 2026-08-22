import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import { createPortal } from 'react-dom'
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { TerminalDockProvider, useTerminalDock } from './contexts/TerminalDockContext'
import liaraLogo from './assets/LIARA-LOGO.png'

// Eager loaded components (needed immediately)
import Login from './components/Login'
import LandingPage from './components/LandingPage'
import ThemeToggle from './components/ThemeToggle'
import LanguageSwitcher from './components/LanguageSwitcher'

// Lazy loaded components (loaded on demand)
const Chat = lazy(() => import('./components/Chat'))
const GuestChat = lazy(() => import('./components/GuestChat'))
const FeaturesPage = lazy(() => import('./components/FeaturesPage'))
const IdentityPage = lazy(() => import('./components/IdentityPage'))
const PrivacyPage = lazy(() => import('./components/PrivacyPage'))
const TechnologyPage = lazy(() => import('./components/TechnologyPage'))
const MoodDashboard = lazy(() => import('./components/MoodDashboard'))
const Config = lazy(() => import('./components/Config'))
const Tasks = lazy(() => import('./components/Tasks'))
const CalendarView = lazy(() => import('./components/CalendarView'))
const NotesFileManager = lazy(() => import('./components/NotesFileManager'))
const LocationConsent = lazy(() => import('./components/LocationConsent'))
const UserSettings = lazy(() => import('./components/UserSettings'))
const UserProfile = lazy(() => import('./components/UserProfile'))
const UserPreferences = lazy(() => import('./components/UserPreferences'))
const PrivacySettings = lazy(() => import('./components/PrivacySettings'))
const ProfileEdit = lazy(() => import('./components/ProfileEdit'))
const SystemHealth = lazy(() => import('./components/SystemHealth'))
const VisionDetect = lazy(() => import('./components/VisionDetect'))
const ActivityLogs = lazy(() => import('./components/ActivityLogs'))
const LogReader = lazy(() => import('./components/admin/LogReader'))
const AdminLayout = lazy(() => import('./components/AdminLayout'))
const AdminDashboard = lazy(() => import('./components/AdminDashboard'))
const UserManagement = lazy(() => import('./components/UserManagement'))
const SystemConfig = lazy(() => import('./components/SystemConfig'))
const ServiceManagement = lazy(() => import('./components/ServiceManagement'))
const TerminalTabs = lazy(() => import('./components/TerminalTabs'))
const UpdateChecker = lazy(() => import('./components/UpdateChecker'))
const Neo4jBrowser = lazy(() => import('./components/Neo4jBrowser'))

// Legal pages - import individual named exports
const Impressum = lazy(() => import('./components/LegalPages').then(module => ({ default: module.Impressum })))
const Datenschutz = lazy(() => import('./components/LegalPages').then(module => ({ default: module.Datenschutz })))
const AGB = lazy(() => import('./components/LegalPages').then(module => ({ default: module.AGB })))
const Cookies = lazy(() => import('./components/LegalPages').then(module => ({ default: module.Cookies })))

import './styles/theme.css'
import './styles/components/chat.css'
import './styles/components/sidebar.css'
import './App.css'

// Loading fallback component
const PageLoader = () => (
  <div className="page-loader">
    <div className="page-loader-content">
      <div className="page-loader-spinner"></div>
      <p className="page-loader-text">Wird geladen...</p>
    </div>
  </div>
)

// Keeps a single <TerminalTabs/> instance alive for the whole app session, so
// open terminal tabs/WebSocket connections survive navigating anywhere in the app.
// Portals its output into AdminLayout's dock spot (stable for as long as /admin/* is
// mounted), or a detached hidden node otherwise, so the component never unmounts.
function PersistentTerminal() {
  const { dockNode } = useTerminalDock()
  const hiddenHomeRef = useRef(null)

  if (!hiddenHomeRef.current) {
    hiddenHomeRef.current = document.createElement('div')
    hiddenHomeRef.current.style.display = 'none'
  }

  useEffect(() => {
    const el = hiddenHomeRef.current
    document.body.appendChild(el)
    return () => {
      document.body.removeChild(el)
    }
  }, [])

  // dockNode stays stable for as long as AdminLayout is mounted (anywhere under /admin),
  // so this only retargets when entering/leaving the admin section, never between its subpages.
  const target = dockNode || hiddenHomeRef.current

  return createPortal(
    <Suspense fallback={<div>Wird geladen...</div>}>
      <TerminalTabs />
    </Suspense>,
    target
  )
}

function App() {
  const { t } = useTranslation()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showLocationConsent, setShowLocationConsent] = useState(false)

  // Check for existing token on mount
  useEffect(() => {
    const isGuestMode = localStorage.getItem('liara_guest_mode') === 'true'
    const token = localStorage.getItem('liara_token')
    const userData = localStorage.getItem('liara_user')
    
    if (isGuestMode) {
      setUser({
        username: 'guest',
        full_name: 'Gast',
        role: 'guest',
        is_guest: true
      })
    } else if (token && userData) {
      try {
        setUser(JSON.parse(userData))
      } catch (error) {
        console.error('Failed to parse user data:', error)
        localStorage.removeItem('liara_token')
        localStorage.removeItem('liara_user')
      }
    }
    
    setLoading(false)
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    // Show location consent modal after successful login (not for guests)
    if (!userData.is_guest) {
      setShowLocationConsent(true)
    }
  }

  const handleLocationConsentComplete = (accepted) => {
    setShowLocationConsent(false)
    if (accepted) {
      console.log('Location consent accepted')
    } else {
      console.log('Location consent declined')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('liara_token')
    localStorage.removeItem('liara_refresh_token')
    localStorage.removeItem('liara_user')
    localStorage.removeItem('liara_guest_mode')
    setUser(null)
  }

  // Show loading state
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Initialisiere Liara...</p>
      </div>
    )
  }

  // Show login if not authenticated
  if (!user) {
    return (
      <Router>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage onLogin={handleLogin} />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/identity" element={<IdentityPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/technology" element={<TechnologyPage />} />
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="/impressum" element={<Impressum />} />
            <Route path="/datenschutz" element={<Datenschutz />} />
            <Route path="/agb" element={<AGB />} />
            <Route path="/cookies" element={<Cookies />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Router>
    )
  }

  const isGuest = user.is_guest === true
  const isAdmin = user.role === 'admin'
  const initials = user.full_name?.split(' ').map(n => n[0]).join('') || 
                   user.username?.charAt(0)?.toUpperCase() || 'U'

  return (
    <Router>
      <TerminalDockProvider>
      <div className="app">
        {/* Keeps terminal sessions alive across the whole app, not just within /admin */}
        {isAdmin && <PersistentTerminal />}

        {/* Location Consent Modal */}
        {showLocationConsent && (
          <LocationConsent onComplete={handleLocationConsentComplete} />
        )}

        {/* Header */}
        <header className="app-header">
          <div className="app-header-content">
            <NavLink to="/chat" className="app-logo">
              <img src={liaraLogo} alt="LIARA" className="app-logo-icon" />
              <span className="app-logo-text">LIARA</span>
            </NavLink>
            
            <div className="user-menu">
              {isGuest && (
                <span className="guest-badge">
                  <span>👋</span>
                  <span>Gast-Modus</span>
                </span>
              )}
              <div className="user-avatar">
                {initials}
              </div>
              <div className="hide-mobile">
                <div className="user-name">{user.full_name || user.username}</div>
                <div className="user-role">{user.role}</div>
              </div>
              <div className="user-actions">
                <LanguageSwitcher />
                <ThemeToggle />
                <button onClick={handleLogout} className="btn btn-ghost btn-sm logout-btn">
                  <span className="hide-mobile">🚪</span>
                  <span className="show-desktop">{t('nav.logout')}</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Navigation */}
        <nav className="app-nav">
          <NavLink to="/chat" className="nav-link">
            <span>💬</span> <span>{t('nav.chat')}</span>
          </NavLink>
          {!isGuest && (
            <>
              <NavLink to="/tasks" className="nav-link">
                <span>✓</span> <span>{t('nav.tasks')}</span>
              </NavLink>
              <NavLink to="/calendar" className="nav-link">
                <span>📅</span> <span>Kalender</span>
              </NavLink>
              <NavLink to="/notes" className="nav-link">
                <span>📝</span> <span>Notizen</span>
              </NavLink>
              <NavLink to="/mood" className="nav-link">
                <span>😊</span> <span>Stimmung</span>
              </NavLink>
              <NavLink to="/vision" className="nav-link">
                <span>👁️</span> <span>Vision</span>
              </NavLink>
              <NavLink to="/settings" className="nav-link">
                <span>👤</span> <span>{t('nav.profile')}</span>
              </NavLink>
            </>
          )}
          {isAdmin && (
            <NavLink to="/admin" className="nav-link">
              <span>🛠️</span> <span>Admin</span>
            </NavLink>
          )}
        </nav>

        {/* Main Content */}
        <main className="app-main">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={isGuest ? <GuestChat /> : <Chat />} />
              
              {!isGuest && (
                <>
                  <Route path="/mood" element={<MoodDashboard />} />
                  <Route path="/config" element={<Config />} />
                  <Route path="/tasks" element={<Tasks />} />
                  <Route path="/calendar" element={<CalendarView />} />
                  <Route path="/notes" element={<NotesFileManager />} />
                  <Route path="/profile" element={<ProfileEdit />} />
                  <Route path="/vision" element={<VisionDetect />} />
                  
                  {/* User Settings with Sub-Routes */}
                  <Route path="/settings" element={<UserSettings />}>
                    <Route index element={<Navigate to="/settings/profile" replace />} />
                    <Route path="profile" element={<UserProfile />} />
                    <Route path="privacy" element={<PrivacySettings />} />
                    <Route path="preferences" element={<UserPreferences />} />
                  </Route>
                </>
              )}

              {isAdmin && (
                <>
                  <Route path="/admin" element={<AdminLayout user={user} onLogout={handleLogout} />}>
                    <Route index element={<AdminDashboard />} />
                    <Route path="dashboard" element={<AdminDashboard />} />
                    <Route path="users" element={<UserManagement />} />
                    <Route path="system" element={<SystemConfig />} />
                    <Route path="logs" element={<LogReader />} />
                    <Route path="health" element={<SystemHealth />} />
                    <Route path="updates" element={<UpdateChecker />} />
                    {/* TerminalTabs lives in PersistentTerminal (app root) so sessions survive nav switches */}
                    <Route path="terminal" element={null} />
                  </Route>
                </>
              )}

              {/* Legal Pages */}
              <Route path="/impressum" element={<Impressum />} />
              <Route path="/datenschutz" element={<Datenschutz />} />
              <Route path="/agb" element={<AGB />} />
              <Route path="/cookies" element={<Cookies />} />
            </Routes>
          </Suspense>
        </main>
      </div>
      </TerminalDockProvider>
    </Router>
  )
}

export default App
