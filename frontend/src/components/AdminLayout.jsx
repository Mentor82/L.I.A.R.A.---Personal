import { useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTerminalDock } from '../contexts/useTerminalDock'
import './AdminLayout.css'

/**
 * Admin Layout
 * Manages admin panel, users, system settings and logs
 */
function AdminLayout({ onLogout }) {
  const location = useLocation()
  const navigate = useNavigate()
  const isTerminalActive = location.pathname === '/admin/terminal'
  const dockRef = useRef(null)
  const { setDockNode } = useTerminalDock()

  // Register our dock spot once, for as long as AdminLayout stays mounted (i.e. anywhere
  // under /admin) - the div itself is never conditionally unmounted (only CSS-hidden), so
  // the portal target stays stable across /admin/dashboard <-> /admin/terminal switches.
  useEffect(() => {
    setDockNode(dockRef.current)
    return () => setDockNode(null)
  }, [setDockNode])

  // Logout handler - delegates to App.jsx's onLogout, which clears the
  // real liara_* auth/session keys and resets the app's user state.
  // This component used to clear its own (wrong, unused) 'token'/'user'
  // keys and navigate to /login without ever calling onLogout, so the
  // real session (liara_token/liara_user) stayed logged in.
  const handleLogout = () => {
    onLogout?.()
    navigate('/login')
  }

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1 className="admin-title">
          <span className="admin-icon">⚡</span>
          Admin Panel
        </h1>
        <p className="admin-subtitle">
          System-Verwaltung, Benutzer und Einstellungen
        </p>
      </div>

      <div className="admin-layout">
        {/* Sidebar Navigation */}
        <nav className="admin-nav">
          <NavLink 
            to="/admin/dashboard" 
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">📊</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Dashboard</span>
              <span className="admin-nav-desc">System Overview</span>
            </div>
          </NavLink>

          <NavLink 
            to="/admin/users" 
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">👥</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Benutzer</span>
              <span className="admin-nav-desc">User Management</span>
            </div>
          </NavLink>

          <NavLink 
            to="/admin/system" 
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">⚙️</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">System</span>
              <span className="admin-nav-desc">System Settings</span>
            </div>
          </NavLink>

          <NavLink 
            to="/admin/logs" 
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">📝</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Logs</span>
              <span className="admin-nav-desc">Activity Logs</span>
            </div>
          </NavLink>

          <NavLink 
            to="/admin/health" 
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">🏥</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Health</span>
              <span className="admin-nav-desc">System Health</span>
            </div>
          </NavLink>

          <NavLink
            to="/admin/terminal"
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">💻</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Terminal</span>
              <span className="admin-nav-desc">System Terminal</span>
            </div>
          </NavLink>

          <NavLink
            to="/admin/updates"
            className={({ isActive }) => `admin-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="admin-nav-icon">🔄</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Updates</span>
              <span className="admin-nav-desc">Git-Status & Patches</span>
            </div>
          </NavLink>

          {/* Logout Button */}
          <button 
            className="admin-nav-item logout-button"
            onClick={handleLogout}
          >
            <span className="admin-nav-icon">🚪</span>
            <div className="admin-nav-content">
              <span className="admin-nav-title">Logout</span>
              <span className="admin-nav-desc">Abmelden</span>
            </div>
          </button>
        </nav>

        {/* Main Content */}
        <div className="admin-main">
          {/* Dock spot for the app-wide persistent terminal - always mounted, only
              CSS-hidden, so the portal target never gets torn down (see TerminalDockContext) */}
          <div style={{ display: isTerminalActive ? 'block' : 'none', height: '100%' }}>
            <div ref={dockRef} style={{ height: '100%' }} />
          </div>
          <div style={{ display: isTerminalActive ? 'none' : 'block', height: '100%' }}>
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminLayout
