import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { THEME_STORAGE_KEY, getStoredTheme, resolveEffectiveTheme, applyTheme } from '../utils/theme';
import liaraLogo from '../assets/LIARA-LOGO.png';
import './PageLayout.css';

// LandingPage.jsx still passes a `showGuestCTA` prop (see its
// `guestModeEnabled`), but there's no guest-CTA UI here yet to gate on it -
// left out of the destructure below rather than wired to nothing.
function PageLayout({ children, wide = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const isLandingPage = location.pathname === '/';
  // Legal pages and /architecture are mounted in BOTH route trees (App.jsx)
  // so they stay reachable while logged in too. When logged in, App.jsx's
  // own header (logo, theme toggle, logout) is already on screen - showing
  // this layout's header on top of it duplicated the logo and, worse, showed
  // "Anmelden"/"Registrieren" buttons for a user who is already signed in.
  const isAuthenticated = Boolean(
    localStorage.getItem('liara_token') || localStorage.getItem('liara_guest_mode') === 'true'
  );

  // Theme State - shares the same liara_theme key/resolution as the
  // authenticated app (ThemeToggle.jsx) instead of its own separate
  // "liara-theme" key, which never synced with it before. This component's
  // toggle is dark/light-only (no "system" option in its UI), so a stored
  // "system" preference is resolved to its effective value up front.
  const [theme, setTheme] = useState(() => resolveEffectiveTheme(getStoredTheme()));

  // index.html's blocking script already applies the theme before first
  // paint site-wide, but apply again here too in case this component ever
  // mounts standalone - cheap, and keeps this page's own state/DOM in sync.
  useEffect(() => {
    applyTheme(theme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    applyTheme(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);
  };

  return (
    <div className="page-layout">
      {/* Header - App.jsx already renders its own when logged in */}
      {!isAuthenticated && (
        <header className="layout-header">
          <div className="layout-header-content">
            <NavLink to="/" className="layout-logo">
              <img src={liaraLogo} alt="LIARA" className="layout-logo-icon" />
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
      )}

      <div className={`layout-content${wide ? ' layout-content-wide' : ''}`}>
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
            <NavLink to="/architecture" className="sidebar-link">
              <span className="sidebar-icon">🧭</span>
              Architektur
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
              <img src={liaraLogo} alt="LIARA" className="footer-logo-icon" />
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
              <NavLink to="/architecture">Architektur</NavLink>
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
              Local-first und selbst gehostet. Optionale Ollama-Cloudmodelle nur bei bewusster
              Auswahl. Keine Tracking-Cookies. Open-Source unter MIT-Lizenz.
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
          <p>&copy; 2026 LIARA Personal. Alle Rechte vorbehalten.</p>
        </div>
      </footer>
    </div>
  );
}

export default PageLayout;
