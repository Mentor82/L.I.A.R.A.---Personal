import { NavLink, Outlet, useLocation } from 'react-router-dom'
import './UserSettings.css'

/**
 * User Settings Layout
 * Manages user profile, privacy, and preferences
 */
function UserSettings() {
  const location = useLocation()
  const isRootPath = location.pathname === '/settings'

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1 className="settings-title">
          <span className="settings-icon">👤</span>
          Benutzer-Einstellungen
        </h1>
        <p className="settings-subtitle">
          Verwalte dein Profil, Privacy-Einstellungen und Präferenzen
        </p>
      </div>

      <div className="settings-layout">
        {/* Sidebar Navigation */}
        <nav className="settings-nav">
          <NavLink 
            to="/settings/profile" 
            className={({ isActive }) => `settings-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="settings-nav-icon">👤</span>
            <div className="settings-nav-content">
              <span className="settings-nav-title">Profil</span>
              <span className="settings-nav-desc">Name, Passwort ändern</span>
            </div>
          </NavLink>

          <NavLink 
            to="/settings/privacy" 
            className={({ isActive }) => `settings-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="settings-nav-icon">🔒</span>
            <div className="settings-nav-content">
              <span className="settings-nav-title">Privacy</span>
              <span className="settings-nav-desc">Daten-Kontrolle & Export</span>
            </div>
          </NavLink>

          <NavLink 
            to="/settings/preferences" 
            className={({ isActive }) => `settings-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="settings-nav-icon">⚙️</span>
            <div className="settings-nav-content">
              <span className="settings-nav-title">Präferenzen</span>
              <span className="settings-nav-desc">AI-Model, Sprache, Theme</span>
            </div>
          </NavLink>
        </nav>

        {/* Main Content */}
        <div className="settings-main">
          {isRootPath ? (
            <div className="settings-welcome">
              <div className="settings-welcome-icon">⚙️</div>
              <h2>Willkommen in den Einstellungen</h2>
              <p>Wähle einen Bereich aus der Navigation links</p>
            </div>
          ) : (
            <Outlet />
          )}
        </div>
      </div>
    </div>
  )
}

export default UserSettings
