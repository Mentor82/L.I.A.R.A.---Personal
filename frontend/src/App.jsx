import { useState, useEffect, useRef, lazy, Suspense } from 'react'
import { createPortal } from 'react-dom'
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { TerminalDockProvider, useTerminalDock } from './contexts/TerminalDockContext'
import { ViewModeProvider, useViewMode } from './contexts/ViewModeContext'
import { preferencesAPI, workspaceAPI } from './services/api'
import liaraLogo from './assets/LIARA-LOGO.png'

// Eager loaded components (needed immediately)
import Login from './components/Login'
import LandingPage from './components/LandingPage'
import ThemeToggle from './components/ThemeToggle'
import LanguageSwitcher from './components/LanguageSwitcher'

// Lazy loaded components (loaded on demand)
const Chat = lazy(() => import('./components/Chat'))
const MobileChat = lazy(() => import('./components/mobile/MobileChat'))
const MobileWorkspace = lazy(() => import('./components/mobile/MobileWorkspace'))
const MobileSettings = lazy(() => import('./components/mobile/MobileSettings'))
const GuestChat = lazy(() => import('./components/GuestChat'))
const FeaturesPage = lazy(() => import('./components/FeaturesPage'))
const IdentityPage = lazy(() => import('./components/IdentityPage'))
const PrivacyPage = lazy(() => import('./components/PrivacyPage'))
const TechnologyPage = lazy(() => import('./components/TechnologyPage'))
const ArchitecturePage = lazy(() => import('./components/ArchitecturePage'))
const WorkspacePage = lazy(() => import('./components/WorkspacePage'))
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

// Synchronous session restore from localStorage - pure reads, no network
// call, so this can run directly as a useState initializer instead of a
// post-mount effect (see App()).
function restoreUserFromStorage() {
  const isGuestMode = localStorage.getItem('liara_guest_mode') === 'true'
  if (isGuestMode) {
    return {
      username: 'guest',
      full_name: 'Gast',
      role: 'guest',
      is_guest: true
    }
  }

  const token = localStorage.getItem('liara_token')
  const userData = localStorage.getItem('liara_user')
  if (token && userData) {
    try {
      return JSON.parse(userData)
    } catch (error) {
      console.error('Failed to parse user data:', error)
      localStorage.removeItem('liara_token')
      localStorage.removeItem('liara_user')
    }
  }

  return null
}

// Every path the unauthenticated tree actually serves - anything else is
// treated as an attempted protected route, so it can be restored after
// login instead of silently discarded (see the !user branch in App()).
const PUBLIC_PATHS = new Set([
  '/', '/features', '/identity', '/privacy', '/technology', '/architecture', '/login',
  '/impressum', '/datenschutz', '/agb', '/cookies'
])

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
  // Restored synchronously during the initial render (not in a useEffect,
  // which used to leave a render where auth state was still "unknown" -
  // harmless for a healthy session since setUser/setLoading batched
  // together, but a real gap for a corrupted/partial localStorage state,
  // see restoreUserFromStorage below). No async check involved (pure
  // localStorage reads), so there's nothing to actually "load".
  const [user, setUser] = useState(restoreUserFromStorage)
  const [showLocationConsent, setShowLocationConsent] = useState(false)
  // Workspace v1 is gated by a per-user preference (toggle lives in
  // UserPreferences.jsx) - defaults to true so the nav item doesn't flicker
  // away for a split second on every load while the real value is fetched.
  const [workspaceEnabled, setWorkspaceEnabled] = useState(true)
  // Agent-Vorbereitung v1: separate opt-in from workspaceEnabled above -
  // defaults false (matches the preference's own default), only used to
  // decide whether the pending-proposals badge polling below is worth doing.
  const [workspaceAgentEnabled, setWorkspaceAgentEnabled] = useState(false)
  const [pendingProposalsCount, setPendingProposalsCount] = useState(0)
  // Captured once, before any redirect can change it, so a reload of a
  // protected route can be restored after login instead of silently
  // falling back to /chat (see the !user branch and handleLogin below).
  const [originalPath] = useState(() => window.location.pathname + window.location.search)

  useEffect(() => {
    if (!user || user.is_guest) return
    preferencesAPI.get()
      .then((prefs) => {
        setWorkspaceEnabled(prefs?.workspace_enabled !== false)
        setWorkspaceAgentEnabled(!!prefs?.workspace_agent_enabled)
      })
      .catch(() => {}) // keep the defaults if this fails - non-critical
  }, [user])

  // Small pending-proposals badge on the Workspace nav item - lets the user
  // notice a proposal from any tab, not just while already on /workspace.
  // Same polling pattern as Chat.jsx's mood refresh (plain setInterval), just
  // a longer interval since this is polish, not something latency-sensitive.
  useEffect(() => {
    if (!user || user.is_guest || !workspaceAgentEnabled) {
      setPendingProposalsCount(0)
      return
    }
    const checkPending = () => {
      const sessionId = parseInt(localStorage.getItem('liara_active_session'), 10)
      if (!sessionId) return
      workspaceAPI.listProposals(sessionId, 'pending')
        .then(({ proposals }) => setPendingProposalsCount(proposals?.length || 0))
        .catch((err) => {
          if (err?.message?.includes('Session not found')) {
            localStorage.removeItem('liara_active_session')
          }
          setPendingProposalsCount(0)
        })
    }
    checkPending()
    const interval = setInterval(checkPending, 15000)
    return () => clearInterval(interval)
  }, [user, workspaceAgentEnabled])

  const handleLogin = (userData) => {
    setUser(userData)
    // Show location consent modal after successful login (not for guests)
    if (!userData.is_guest) {
      setShowLocationConsent(true)
    }
    // Restore the route the user actually asked for (see the !user
    // branch's redirect to /login?redirect=...) - window.history, not
    // useNavigate(), since this fires before the authenticated <Router>
    // (a fresh BrowserRouter instance) has mounted; it reads the address
    // bar fresh on the very next render, after this synchronously corrects it.
    const redirectTo = new URLSearchParams(window.location.search).get('redirect')
    const target = redirectTo && redirectTo.startsWith('/') && !redirectTo.startsWith('//') ? redirectTo : '/chat'
    window.history.replaceState(null, '', target)
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
    // Chat state is cached per-browser, not per-account - without this,
    // the next account to log in on this browser sees the previous
    // account's cached chat sessions until it has sessions of its own.
    localStorage.removeItem('liara_chat_sessions')
    localStorage.removeItem('liara_active_session')
    localStorage.removeItem('liara_selected_model')
    localStorage.removeItem('liara_auto_model')
    setUser(null)
  }

  // Show login if not authenticated
  if (!user) {
    // A path that isn't one of the pages this tree actually serves means
    // the user (or a corrupted/partial session) landed here trying to
    // reach a protected route - send them through /login with it attached
    // instead of the old blind "*" -> "/" (which erased it) so handleLogin
    // can restore it after a successful sign-in.
    const requestedPath = originalPath.split('?')[0]
    const catchAllTarget = PUBLIC_PATHS.has(requestedPath)
      ? '/'
      : `/login?redirect=${encodeURIComponent(originalPath)}`

    return (
      <Router>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage onLogin={handleLogin} />} />
            <Route path="/features" element={<FeaturesPage />} />
            <Route path="/identity" element={<IdentityPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/technology" element={<TechnologyPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="/impressum" element={<Impressum />} />
            <Route path="/datenschutz" element={<Datenschutz />} />
            <Route path="/agb" element={<AGB />} />
            <Route path="/cookies" element={<Cookies />} />
            <Route path="*" element={<Navigate to={catchAllTarget} replace />} />
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
      <ViewModeProvider>
        <TerminalDockProvider>
          <AuthenticatedApp
            user={user}
            isGuest={isGuest}
            isAdmin={isAdmin}
            initials={initials}
            handleLogout={handleLogout}
            showLocationConsent={showLocationConsent}
            handleLocationConsentComplete={handleLocationConsentComplete}
            workspaceEnabled={workspaceEnabled}
            pendingProposalsCount={pendingProposalsCount}
          />
        </TerminalDockProvider>
      </ViewModeProvider>
    </Router>
  )
}

function AuthenticatedApp({
  user, isGuest, isAdmin, initials, handleLogout,
  showLocationConsent, handleLocationConsentComplete,
  workspaceEnabled, pendingProposalsCount
}) {
  const { t } = useTranslation()
  const { isMobile, setViewMode } = useViewMode()

  // In Mobile View, render the focused ChatGPT/Copilot style UI
  if (isMobile) {
    return (
      <div className="app mobile-mode">
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={isGuest ? <GuestChat /> : <MobileChat user={user} onLogout={handleLogout} />} />
            <Route path="/workspace" element={<MobileWorkspace />} />
            <Route path="/settings" element={<MobileSettings user={user} onLogout={handleLogout} />} />
            <Route path="/config" element={<MobileSettings user={user} onLogout={handleLogout} />} />
            <Route path="/health" element={<SystemHealth />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </Suspense>
      </div>
    )
  }

  // Full Desktop View
  return (
    <div className="app">
      {isAdmin && <PersistentTerminal />}
      {showLocationConsent && <LocationConsent onComplete={handleLocationConsentComplete} />}

      <header className="app-header">
        <div className="app-header-content">
          <NavLink to="/chat" className="app-logo">
            <img src={liaraLogo} alt="LIARA" className="app-logo-icon" />
            <span className="app-logo-text">LIARA</span>
          </NavLink>
          
          <div className="user-menu">
            {isGuest && (
              <span className="guest-badge"><span>👋</span><span>Gast-Modus</span></span>
            )}
            <div className="user-avatar">{initials}</div>
            <div className="hide-mobile">
              <div className="user-name">{user.full_name || user.username}</div>
              <div className="user-role">{user.role}</div>
            </div>
            <div className="user-actions">
              <button
                onClick={() => setViewMode('mobile')}
                className="btn btn-ghost btn-sm"
                title={t('mobile.switchMobile')}
              >
                📱
              </button>
              <NavLink to="/architecture" className="btn btn-ghost btn-sm" title="Architektur-Übersicht">
                🧭
              </NavLink>
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
        <NavLink to="/chat" className="nav-link"><span>💬</span> <span>{t('nav.chat')}</span></NavLink>
        {!isGuest && (
          <>
            <NavLink to="/tasks" className="nav-link"><span>✓</span> <span>{t('nav.tasks')}</span></NavLink>
            <NavLink to="/calendar" className="nav-link"><span>📅</span> <span>Kalender</span></NavLink>
            <NavLink to="/notes" className="nav-link"><span>📝</span> <span>Notizen</span></NavLink>
            {workspaceEnabled && (
              <NavLink to="/workspace" className="nav-link">
                <span>🗂️</span> <span>Workspace</span>
                {pendingProposalsCount > 0 && <span className="nav-badge">{pendingProposalsCount}</span>}
              </NavLink>
            )}
            <NavLink to="/mood" className="nav-link"><span>😊</span> <span>Stimmung</span></NavLink>
            <NavLink to="/vision" className="nav-link"><span>👁️</span> <span>Vision</span></NavLink>
            <NavLink to="/settings" className="nav-link"><span>👤</span> <span>{t('nav.profile')}</span></NavLink>
          </>
        )}
        {isAdmin && <NavLink to="/admin" className="nav-link"><span>🛠️</span> <span>Admin</span></NavLink>}
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
                {workspaceEnabled && <Route path="/workspace" element={<WorkspacePage />} />}
                <Route path="/profile" element={<ProfileEdit />} />
                <Route path="/vision" element={<VisionDetect />} />
                <Route path="/settings" element={<UserSettings />}>
                  <Route index element={<Navigate to="/settings/profile" replace />} />
                  <Route path="profile" element={<UserProfile />} />
                  <Route path="privacy" element={<PrivacySettings />} />
                  <Route path="preferences" element={<UserPreferences />} />
                </Route>
              </>
            )}
            {isAdmin && (
              <Route path="/admin" element={<AdminLayout user={user} onLogout={handleLogout} />}>
                <Route index element={<AdminDashboard />} />
                <Route path="dashboard" element={<AdminDashboard />} />
                <Route path="users" element={<UserManagement />} />
                <Route path="system" element={<SystemConfig />} />
                <Route path="logs" element={<LogReader />} />
                <Route path="health" element={<SystemHealth />} />
                <Route path="updates" element={<UpdateChecker />} />
                <Route path="terminal" element={null} />
              </Route>
            )}
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/impressum" element={<Impressum />} />
            <Route path="/datenschutz" element={<Datenschutz />} />
            <Route path="/agb" element={<AGB />} />
            <Route path="/cookies" element={<Cookies />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}

export default App
