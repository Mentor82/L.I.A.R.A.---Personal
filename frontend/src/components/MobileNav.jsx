import { useState } from 'react';
import './MobileNav.css';

function MobileNav({ isGuest, onLogout, user }) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => setIsOpen(!isOpen);
  const closeMenu = () => setIsOpen(false);

  const navItems = [
    { path: '/', label: 'Chat', icon: '💬', guest: true },
    { path: '/mood', label: 'Stimmung', icon: '🌙', guest: false },
    { path: '/config', label: 'Config', icon: '⚙️', guest: false },
    { path: '/tasks', label: 'Aufgaben', icon: '✅', guest: false },
    { path: '/calendar', label: 'Kalender', icon: '📅', guest: false },
    { path: '/notes', label: 'Notizen', icon: '📝', guest: false },
    { path: '/privacy', label: 'Datenschutz', icon: '🔒', guest: true },
    { path: '/admin', label: 'Admin Panel', icon: '👑', guest: false, adminOnly: true },
  ];

  const legalItems = [
    { path: '/impressum', label: 'Impressum', icon: 'ℹ️' },
    { path: '/datenschutz', label: 'Datenschutzerklärung', icon: '🛡️' },
    { path: '/agb', label: 'AGB', icon: '📄' },
    { path: '/cookies', label: 'Cookie-Richtlinie', icon: '🍪' },
  ];

  return (
    <>
      {/* Hamburger Button */}
      <button 
        className={`mobile-menu-toggle ${isOpen ? 'active' : ''}`}
        onClick={toggleMenu}
        aria-label="Menu"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>

      {/* Overlay */}
      {isOpen && (
        <div className="mobile-menu-overlay" onClick={closeMenu}></div>
      )}

      {/* Slide-in Menu */}
      <nav className={`mobile-menu ${isOpen ? 'open' : ''}`}>
        <div className="mobile-menu-header halo-panel">
          <div className="mobile-menu-user">
            <div className="mobile-user-avatar">
              {isGuest ? '👋' : '🌙'}
            </div>
            <div className="mobile-user-info">
              <div className="halo-header" style={{ marginBottom: '0.25rem' }}>
                {user.username}
              </div>
              <div className="halo-mono" style={{ fontSize: '0.7rem' }}>
                {isGuest ? 'GUEST MODE' : user.email}
              </div>
              {isGuest && (
                <span className="halo-badge" style={{ fontSize: '0.65rem', marginTop: '0.25rem' }}>
                  Eingeschränkt
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mobile-menu-items">
          <div className="mobile-menu-section">
            <div className="mobile-menu-section-title halo-mono">
              NAVIGATION
            </div>
            {navItems
              .filter(item => {
                if (isGuest && !item.guest) return false;
                if (item.adminOnly && user?.role !== 'admin') return false;
                return true;
              })
              .map(item => (
                <a
                  key={item.path}
                  href={item.path}
                  className="mobile-menu-item"
                  onClick={closeMenu}
                >
                  <span className="mobile-menu-icon">{item.icon}</span>
                  <span className="mobile-menu-label">{item.label}</span>
                  <span className="mobile-menu-arrow">▸</span>
                </a>
              ))}
          </div>

          <div className="halo-divider"></div>

          <div className="mobile-menu-section">
            <div className="mobile-menu-section-title halo-mono">
              RECHTLICHES
            </div>
            {legalItems.map(item => (
              <a
                key={item.path}
                href={item.path}
                className="mobile-menu-item mobile-menu-item-small"
                onClick={closeMenu}
              >
                <span className="mobile-menu-icon">{item.icon}</span>
                <span className="mobile-menu-label">{item.label}</span>
                <span className="mobile-menu-arrow">▸</span>
              </a>
            ))}
          </div>
        </div>

        <div className="mobile-menu-footer">
          <button 
            className="mobile-logout-btn halo-button"
            onClick={() => {
              closeMenu();
              onLogout();
            }}
          >
            {isGuest ? '🚪 Verlassen' : '🚪 Abmelden'}
          </button>
        </div>
      </nav>
    </>
  );
}

export default MobileNav;
