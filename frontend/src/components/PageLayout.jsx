import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import './PageLayout.css';

function PageLayout({ children, showGuestCTA = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const isLandingPage = location.pathname === '/';
  
  // Theme State
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('liara-theme');
    if (savedTheme) return savedTheme;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  });

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('liara-theme', newTheme);
  };

  return (
    <div className="page-layout">
      {/* Header */}
      <header className="layout-header">
        <div className="layout-header-content">
          <NavLink to="/" className="layout-logo">
            <span className="layout-logo-icon">🌙</span>
            <span className="layout-logo-text">LIARA</span>
            <span className="layout-logo-tagline">Digitalbegleiterin</span>
          </NavLink>
          
          <div className="layout-header-buttons">
            <button 
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <button 
              className="btn btn-ghost" 
              onClick={() => navigate('/?showAuth=true&register=true')}
            >
              Registrieren
            </button>
            <button 
              className="btn btn-primary" 
              onClick={() => navigate('/?showAuth=true')}
            >
              Anmelden
            </button>
          </div>
        </div>
      </header>

      <div className="layout-content">
        {/* Sidebar */}
        <aside className="layout-sidebar">
          <div className="sidebar-header">
            <h3 className="sidebar-title">Entdecke Liara</h3>
            {!isLandingPage && (
              <NavLink to="/" className="sidebar-home-btn" title="Zur Startseite">
                🏠
              </NavLink>
            )}
          </div>
          <nav className="sidebar-nav">
            <NavLink to="/features" className="sidebar-link">
              <span className="sidebar-icon">✨</span>
              Features
            </NavLink>
            <NavLink to="/identity" className="sidebar-link">
              <span className="sidebar-icon">💜</span>
              Identity Codex
            </NavLink>
            <NavLink to="/privacy" className="sidebar-link">
              <span className="sidebar-icon">🔒</span>
              Datenschutz
            </NavLink>
            <NavLink to="/technology" className="sidebar-link">
              <span className="sidebar-icon">🤖</span>
              Technologie
            </NavLink>
            <NavLink to="/impressum" className="sidebar-link">
              <span className="sidebar-icon">📄</span>
              Impressum
            </NavLink>
            <NavLink to="/datenschutz" className="sidebar-link">
              <span className="sidebar-icon">🛡️</span>
              Datenschutzerklärung
            </NavLink>
            <NavLink to="/agb" className="sidebar-link">
              <span className="sidebar-icon">📋</span>
              AGB
            </NavLink>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="layout-main">
          {children}
        </main>
      </div>

      {/* Footer */}
      <footer className="layout-footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <span className="footer-logo-icon">🌙</span>
              <span className="footer-logo-text">LIARA</span>
            </div>
            <p className="footer-description">
              Deine persönliche, privacy-first Digitalbegleiterin
            </p>
          </div>

          <div className="footer-section">
            <h4>Navigation</h4>
            <nav className="footer-nav">
              <NavLink to="/features">Features</NavLink>
              <NavLink to="/privacy">Datenschutz</NavLink>
              <NavLink to="/technology">Technologie</NavLink>
            </nav>
          </div>

          <div className="footer-section">
            <h4>Rechtliches</h4>
            <nav className="footer-nav">
              <NavLink to="/impressum">Impressum</NavLink>
              <NavLink to="/datenschutz">Datenschutzerklärung</NavLink>
              <NavLink to="/agb">AGB</NavLink>
              <NavLink to="/cookies">Cookie-Richtlinie</NavLink>
            </nav>
          </div>

          <div className="footer-section">
            <h4>Open Source & Privacy</h4>
            <p className="footer-description">
              100% lokal. Keine Cloud. Keine Tracking-Cookies. Open-Source unter MIT-Lizenz.
              International compliant: DSGVO, UK GDPR, CCPA, PIPEDA & APAC.
            </p>
            <a 
              href="https://github.com/yourusername/liara" 
              target="_blank" 
              rel="noopener noreferrer"
              className="footer-github"
            >
              <span>⭐</span> GitHub
            </a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>&copy; 2024 Liara AI Assistant. Alle Rechte vorbehalten.</p>
        </div>
      </footer>
    </div>
  );
}

export default PageLayout;
