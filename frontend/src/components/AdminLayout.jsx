import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import './AdminLayout.css'

/**
 * Admin Layout
 * Manages admin panel, users, system settings and logs
 */
function AdminLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const isRootPath = location.pathname === '/admin'

  // Logout handler
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
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
          <Outlet />
        </div>
      </div>
    </div>
  )
}

export default AdminLayout
