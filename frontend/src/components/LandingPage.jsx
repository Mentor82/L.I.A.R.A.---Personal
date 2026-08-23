import { useState, useEffect } from 'react';
import { useNavigate, NavLink, useLocation } from 'react-router-dom';
import { guestAPI } from '../services/guestApi';
import PageLayout from './PageLayout';
import ComplianceBadges from './ComplianceBadges';
import './LandingPage.css';

function LandingPage({ onLogin }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [guestModeEnabled, setGuestModeEnabled] = useState(false);
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    full_name: '',
    phone: '',
    date_of_birth: '',
    country: '',
    language: 'de',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    newsletter_opt_in: false,
    privacy_accepted: false,
    terms_accepted: false
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Guest Chat State
  const [guestMessages, setGuestMessages] = useState([]);
  const [guestInput, setGuestInput] = useState('');
  const [guestLoading, setGuestLoading] = useState(false);
  const [guestInitialized, setGuestInitialized] = useState(false);
  
  // Guest Chat Overlay State
  const [showGuestChat, setShowGuestChat] = useState(false);
  const [chatPosition, setChatPosition] = useState({ x: window.innerWidth - 420, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Check if guest mode is enabled
  useEffect(() => {
    const checkGuestMode = async () => {
      try {
        const response = await fetch('/api/public/guest-mode');
        if (response.ok) {
          const data = await response.json();
          setGuestModeEnabled(data.guest_mode_enabled || false);
        }
      } catch (error) {
        console.error('Failed to check guest mode:', error);
      }
    };
    checkGuestMode();
  }, []);

  // Check URL params for auth mode
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('showAuth') === 'true') {
      setShowAuthForm(true);
      setIsRegistering(params.get('register') === 'true');
      // Clean URL
      window.history.replaceState({}, '', '/');
    }
  }, [location]);

  // Initialize guest chat
  useEffect(() => {
    const initGuestChat = async () => {
      if (!guestModeEnabled || guestInitialized) return;
      
      try {
        const { message, status } = await guestAPI.getWelcome();
        if (status === 403) {
          setGuestModeEnabled(false);
          return;
        }
        setGuestMessages([{ role: 'assistant', content: message }]);
        setGuestInitialized(true);
      } catch (error) {
        console.error('Failed to initialize guest chat:', error);
      }
    };
    
    if (guestModeEnabled) {
      initGuestChat();
    }
  }, [guestModeEnabled, guestInitialized]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('liara_token', data.access_token);
        localStorage.setItem('liara_refresh_token', data.refresh_token);
        localStorage.setItem('liara_user', JSON.stringify(data.user));
        onLogin(data.user);
      } else {
        setError(data.detail || 'Login fehlgeschlagen');
      }
    } catch (error) {
      setError('Verbindungsfehler');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (registerForm.password !== registerForm.password_confirm) {
      setError('Passwörter stimmen nicht überein');
      return;
    }

    if (registerForm.password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein');
      return;
    }

    if (!registerForm.privacy_accepted || !registerForm.terms_accepted) {
      setError('Bitte akzeptiere die Datenschutzerklärung und AGB');
      return;
    }

    setLoading(true);

    try {
      // Build request body with only non-empty values
      const body = {
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
        full_name: registerForm.full_name,
        privacy_accepted: registerForm.privacy_accepted
      };

      // Add optional fields if provided
      if (registerForm.phone?.trim()) body.phone = registerForm.phone;
      if (registerForm.date_of_birth) body.date_of_birth = new Date(registerForm.date_of_birth).toISOString();
      if (registerForm.country) body.country = registerForm.country;
      if (registerForm.language) body.language = registerForm.language;
      if (registerForm.timezone) body.timezone = registerForm.timezone;
      if (registerForm.newsletter_opt_in) body.newsletter_opt_in = registerForm.newsletter_opt_in;

      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const data = await response.json();

      if (response.ok) {
        // Auto-login after registration
        localStorage.setItem('liara_token', data.access_token);
        localStorage.setItem('liara_refresh_token', data.refresh_token);
        localStorage.setItem('liara_user', JSON.stringify(data.user));
        onLogin(data.user);
      } else {
        const errorMsg = typeof data.detail === 'string' 
          ? data.detail 
          : Array.isArray(data.detail) 
            ? data.detail.map(e => e.msg || e).join(', ')
            : 'Registrierung fehlgeschlagen';
        setError(errorMsg);
      }
    } catch (error) {
      setError('Verbindungsfehler: ' + (error.message || 'Unbekannter Fehler'));
    } finally {
      setLoading(false);
    }
  };

  const handleGuestMessage = async (e) => {
    e.preventDefault();
    if (!guestInput.trim() || guestLoading) return;

    const userMessage = guestInput.trim();
    setGuestInput('');
    setGuestMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setGuestLoading(true);

    try {
      const data = await guestAPI.sendMessage(userMessage);
      // Backend gibt 'response' zurück, nicht 'message'
      const responseText = data.response || data.message;
      setGuestMessages(prev => [...prev, { role: 'assistant', content: responseText }]);
    } catch (error) {
      // Error handling für 403 (Guest Mode deaktiviert)
      if (error.message && error.message.includes('403')) {
        setGuestMessages(prev => [...prev, { 
          role: 'system', 
          content: '🔒 Der Gast-Modus wurde deaktiviert. Bitte registriere dich für den vollen Zugriff.' 
        }]);
        setGuestModeEnabled(false);
      } else {
        setGuestMessages(prev => [...prev, { 
          role: 'system', 
          content: 'Fehler beim Senden der Nachricht: ' + (error.message || 'Unbekannter Fehler') 
        }]);
      }
    } finally {
      setGuestLoading(false);
    }
  };

  // Drag handlers for guest chat overlay
  const handleMouseDown = (e) => {
    // Nur beim Header-Element draggen, nicht bei Buttons
    if (e.target.classList.contains('guest-chat-header-overlay') || 
        e.target.closest('.guest-chat-header-overlay') && !e.target.closest('button')) {
      e.preventDefault();
      setIsDragging(true);
      setDragOffset({
        x: e.clientX - chatPosition.x,
        y: e.clientY - chatPosition.y
      });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setChatPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  return (
    <>
      <PageLayout 
        showGuestCTA={guestModeEnabled}
      >
        {/* Main Content */}
        <div className="landing-main">
          {/* Show Auth Form or Main Content */}
          {showAuthForm ? (
            /* Login/Register Section */
            <section className="auth-section-centered">
              <button 
                className="back-to-home-btn"
                onClick={() => setShowAuthForm(false)}
                title="Zurück zur Startseite"
              >
                ← Zurück zur Startseite
              </button>
              
              <div className="auth-container">
                {!isRegistering ? (
                  <div className="auth-form-wrapper">
                    <h2 className="auth-title">Anmelden</h2>
                    <p className="auth-subtitle">Greife auf deine persönliche Liara-Instanz zu</p>
                    
                    {error && <div className="auth-error">{error}</div>}
                    
                    <form onSubmit={handleLogin} className="auth-form">
                      <div className="form-group">
                        <label>Benutzername</label>
                        <input
                          type="text"
                          value={loginForm.username}
                          onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                          placeholder="dein-username"
                          required
                        />
                      </div>
                      
                      <div className="form-group">
                        <label>Passwort</label>
                        <input
                          type="password"
                          value={loginForm.password}
                          onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                          placeholder="••••••••"
                          required
                        />
                      </div>

                      <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? 'Anmelden...' : 'Anmelden'}
                      </button>
                    </form>

                    <p className="auth-switch">
                      Noch kein Konto? 
                      <button onClick={() => setIsRegistering(true)} className="link-button">
                        Jetzt registrieren
                      </button>
                    </p>
                  </div>
                ) : (
                  <div className="auth-form-wrapper">
                    <h2 className="auth-title">Registrieren</h2>
                    <p className="auth-subtitle">Erstelle deinen Liara-Account</p>
                    
                    {error && <div className="auth-error">{error}</div>}
                    
                    <form onSubmit={handleRegister} className="auth-form">
                      {/* Personal Information */}
                      <div className="form-section">
                        <h3 className="form-section-title">Persönliche Informationen</h3>
                        
                        <div className="form-row">
                          <div className="form-group">
                            <label>Vollständiger Name *</label>
                            <input
                              type="text"
                              value={registerForm.full_name}
                              onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })}
                              placeholder="Max Mustermann"
                              required
                            />
                          </div>

                          <div className="form-group">
                            <label>E-Mail *</label>
                            <input
                              type="email"
                              value={registerForm.email}
                              onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                              placeholder="max@beispiel.de"
                              required
                            />
                          </div>
                        </div>

                        <div className="form-row">
                          <div className="form-group">
                            <label>Telefon (optional)</label>
                            <input
                              type="tel"
                              value={registerForm.phone}
                              onChange={(e) => setRegisterForm({ ...registerForm, phone: e.target.value })}
                              placeholder="+49 123 456789"
                            />
                          </div>

                          <div className="form-group">
                            <label>Geburtsdatum (optional)</label>
                            <input
                              type="date"
                              value={registerForm.date_of_birth}
                              onChange={(e) => setRegisterForm({ ...registerForm, date_of_birth: e.target.value })}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Account Information */}
                      <div className="form-section">
                        <h3 className="form-section-title">Account-Informationen</h3>
                        
                        <div className="form-group">
                          <label>Benutzername *</label>
                          <input
                            type="text"
                            value={registerForm.username}
                            onChange={(e) => setRegisterForm({ ...registerForm, username: e.target.value })}
                            placeholder="max-mustermann"
                            required
                            minLength={3}
                          />
                          <small className="form-hint">Mindestens 3 Zeichen</small>
                        </div>

                        <div className="form-row">
                          <div className="form-group">
                            <label>Passwort *</label>
                            <input
                              type="password"
                              value={registerForm.password}
                              onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                              placeholder="••••••••"
                              required
                              minLength={8}
                            />
                            <small className="form-hint">Mindestens 8 Zeichen</small>
                          </div>
                      
                          <div className="form-group">
                            <label>Passwort bestätigen *</label>
                            <input
                              type="password"
                              value={registerForm.password_confirm}
                              onChange={(e) => setRegisterForm({ ...registerForm, password_confirm: e.target.value })}
                              placeholder="••••••••"
                              required
                            />
                          </div>
                        </div>
                      </div>

                      {/* Regional Settings */}
                      <div className="form-section">
                        <h3 className="form-section-title">Regionale Einstellungen</h3>
                        
                        <div className="form-row">
                          <div className="form-group">
                            <label>Land (optional)</label>
                            <select
                              value={registerForm.country}
                              onChange={(e) => setRegisterForm({ ...registerForm, country: e.target.value })}
                            >
                              <option value="">Bitte wählen</option>
                              <option value="DE">🇩🇪 Deutschland</option>
                              <option value="AT">🇦🇹 Österreich</option>
                              <option value="CH">🇨🇭 Schweiz</option>
                              <option value="US">🇺🇸 USA</option>
                              <option value="GB">🇬🇧 Großbritannien</option>
                              <option value="FR">🇫🇷 Frankreich</option>
                              <option value="IT">🇮🇹 Italien</option>
                              <option value="ES">🇪🇸 Spanien</option>
                              <option value="NL">🇳🇱 Niederlande</option>
                              <option value="CA">🇨🇦 Kanada</option>
                              <option value="AU">🇦🇺 Australien</option>
                              <option value="JP">🇯🇵 Japan</option>
                              <option value="KR">🇰🇷 Südkorea</option>
                              <option value="CN">🇨🇳 China</option>
                              <option value="SG">🇸🇬 Singapur</option>
                            </select>
                          </div>

                          <div className="form-group">
                            <label>Sprache *</label>
                            <select
                              value={registerForm.language}
                              onChange={(e) => setRegisterForm({ ...registerForm, language: e.target.value })}
                              required
                            >
                              <option value="de">🇩🇪 Deutsch</option>
                              <option value="en">🇬🇧 English</option>
                              <option value="fr">🇫🇷 Français</option>
                              <option value="es">🇪🇸 Español</option>
                              <option value="it">🇮🇹 Italiano</option>
                              <option value="nl">🇳🇱 Nederlands</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      {/* Privacy & Consent */}
                      <div className="form-section">
                        <h3 className="form-section-title">Datenschutz & Einwilligung</h3>
                        
                        <div className="form-checkbox">
                          <input
                            type="checkbox"
                            id="privacy"
                            checked={registerForm.privacy_accepted}
                            onChange={(e) => setRegisterForm({ ...registerForm, privacy_accepted: e.target.checked })}
                            required
                          />
                          <label htmlFor="privacy">
                            Ich akzeptiere die <a href="/datenschutz" target="_blank">Datenschutzerklärung</a> * (DSGVO-konform)
                          </label>
                        </div>

                        <div className="form-checkbox">
                          <input
                            type="checkbox"
                            id="terms"
                            checked={registerForm.terms_accepted}
                            onChange={(e) => setRegisterForm({ ...registerForm, terms_accepted: e.target.checked })}
                            required
                          />
                          <label htmlFor="terms">
                            Ich akzeptiere die <a href="/agb" target="_blank">Allgemeinen Geschäftsbedingungen</a> *
                          </label>
                        </div>

                        <div className="form-checkbox">
                          <input
                            type="checkbox"
                            id="newsletter"
                            checked={registerForm.newsletter_opt_in}
                            onChange={(e) => setRegisterForm({ ...registerForm, newsletter_opt_in: e.target.checked })}
                          />
                          <label htmlFor="newsletter">
                            Newsletter abonnieren (optional)
                          </label>
                        </div>

                        <div className="form-info">
                          <p>🔒 Local-first und selbst gehostet. Deine Daten bleiben bei dir - Ollama-Cloudmodelle nur bei bewusster Auswahl.</p>
                          <p>🌍 International compliant: DSGVO, UK GDPR, CCPA, PIPEDA</p>
                        </div>
                      </div>

                      <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                        {loading ? 'Registrieren...' : 'Account erstellen'}
                      </button>
                    </form>

                    <p className="auth-switch">
                      Bereits registriert? 
                      <button onClick={() => setIsRegistering(false)} className="link-button">
                        Zum Login
                      </button>
                    </p>
                  </div>
                )}
              </div>
            </section>
          ) : (
            <>
              {/* AI Disclosure Banner */}
              <section className="ai-disclosure-landing">
                <div className="ai-disclosure-banner-compact">
                  <div className="ai-disclosure-icon-compact">⚠️</div>
                  <div className="ai-disclosure-content-compact">
                    <strong>LIARA ist ein KI-System</strong> – Alle Antworten werden durch künstliche Intelligenz generiert. 
                    <NavLink to="/technology" className="ai-disclosure-link">Mehr zur KI-Transparenz →</NavLink>
                  </div>
                </div>
              </section>

              {/* Hero Section */}
              <section className="hero-section">
                <div className="hero-content">
                  <div className="hero-badge">🌌 "Fascinating patterns..." – Powered by Aether Neural Matrix</div>
                  
                  <h1 className="hero-title-modern">
                    <span className="hero-welcome">Willkommen bei</span>
                    <span className="hero-name gradient-glow">LIARA</span>
                    <span className="hero-acronym">Local Intelligent Autonomous Reasoning Assistant</span>
                  </h1>
                  
                  <p className="hero-subtitle-modern">
                    Deine persönliche <strong>Privacy-First</strong> KI-Assistentin.
                    <br />
                    Produktivität, Organisation und smarte Gespräche – <em>lokal</em> und <em>sicher</em>.
                  </p>
                  
                  <div className="hero-cta">
                    <button 
                      className="btn btn-hero-primary"
                      onClick={() => setShowAuthForm(true)}
                    >
                      <span className="btn-icon">🚀</span>
                      Kostenlos starten
                    </button>
                    <button 
                      className="btn btn-hero-secondary"
                      onClick={() => window.location.href = '/features'}
                    >
                      <span className="btn-icon">✨</span>
                      Features entdecken
                    </button>
                  </div>
                  
                  <div className="hero-features-modern">
                    <div className="hero-feature-modern">
                      <span className="feature-icon-large">🔮</span>
                      <span className="feature-label">Quantum Archive</span>
                    </div>
                    <div className="hero-feature-modern">
                      <span className="feature-icon-large">🎭</span>
                      <span className="feature-label">Sentiment AI</span>
                    </div>
                    <div className="hero-feature-modern">
                      <span className="feature-icon-large">🕵️</span>
                      <span className="feature-label">Secure Data Network</span>
                    </div>
                    <div className="hero-feature-modern">
                      <span className="feature-icon-large">🎨</span>
                      <span className="feature-label">Image Generation</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* Compliance & Trust Section */}
              <section className="compliance-section-landing">
                <ComplianceBadges />
              </section>

              {/* Main Features Showcase */}
              <section className="main-features-section">
                <h2 className="section-title-main">Deine Werkzeuge für maximale Produktivität</h2>
                <p className="section-subtitle">Alles was du brauchst, um organisiert und fokussiert zu bleiben</p>
                
                <div className="feature-cards-grid">
                  {/* Chat Feature */}
                  <div className="feature-card">
                    <div className="feature-card-header">
                      <div className="feature-card-icon">💬</div>
                      <h3 className="feature-card-title">Intelligenter Chat</h3>
                    </div>
                    <p className="feature-card-description">
                      Unterhalte dich natürlich mit Liara. <em>"Fascinating patterns..."</em> – 
                      Sie erinnert sich an Kontext, versteht deine Stimmung und passt sich deinem Stil an.
                    </p>
                    <ul className="feature-card-list">
                      <li>✓ 4D Memory – erinnert sich an alles</li>
                      <li>✓ Sentiment-Analyse in Echtzeit</li>
                      <li>✓ Multimodal (Text + Bilder)</li>
                    </ul>
                    <button 
                      className="feature-card-cta"
                      onClick={() => setShowAuthForm(true)}
                    >
                      Jetzt chatten →
                    </button>
                  </div>

                  {/* Tasks Feature */}
                  <div className="feature-card">
                    <div className="feature-card-header">
                      <div className="feature-card-icon">✓</div>
                      <h3 className="feature-card-title">Smart Tasks</h3>
                    </div>
                    <p className="feature-card-description">
                      Verwalte deine Aufgaben intelligent. Liara erkennt Prioritäten, 
                      schlägt Deadlines vor und hilft dir beim Fokussieren.
                    </p>
                    <ul className="feature-card-list">
                      <li>✓ Automatische Priorisierung</li>
                      <li>✓ Kategorien & Tags</li>
                      <li>✓ Deadline-Tracking</li>
                    </ul>
                    <button 
                      className="feature-card-cta"
                      onClick={() => setShowAuthForm(true)}
                    >
                      Tasks erstellen →
                    </button>
                  </div>

                  {/* Memory Feature */}
                  <div className="feature-card">
                    <div className="feature-card-header">
                      <div className="feature-card-icon">🔮</div>
                      <h3 className="feature-card-title">Quantum Memory Core</h3>
                    </div>
                    <p className="feature-card-description">
                      Fortgeschrittenes 4D-Gedächtnis mit Quantum-Speichertechnologie.
                      Emotional, episodisch, semantisch und prozedural – wie ein menschliches Langzeitgedächtnis.
                    </p>
                    <ul className="feature-card-list">
                      <li>✓ Neo4j Knowledge Graph (Encrypted Storage)</li>
                      <li>✓ Emotionale Verbindungen (menschlich)</li>
                      <li>✓ Langzeit-Erinnerungen über Jahre</li>
                    </ul>
                    <button 
                      className="feature-card-cta"
                      onClick={() => setShowAuthForm(true)}
                    >
                      Memory erkunden →
                    </button>
                  </div>

                  {/* Image Generation Feature */}
                  <div className="feature-card">
                    <div className="feature-card-header">
                      <div className="feature-card-icon">🎨</div>
                      <h3 className="feature-card-title">Bild-Generierung</h3>
                    </div>
                    <p className="feature-card-description">
                      Erstelle Bilder direkt im Chat – komplett lokal mit Stable Diffusion. 
                      Keine Cloud, keine Limits, 100% Privacy.
                    </p>
                    <ul className="feature-card-list">
                      <li>✓ Stable Diffusion lokal</li>
                      <li>✓ Privacy-First (keine Cloud)</li>
                      <li>✓ Unbegrenzte Generierungen</li>
                    </ul>
                    <button 
                      className="feature-card-cta"
                      onClick={() => setShowAuthForm(true)}
                    >
                      Bilder erstellen →
                    </button>
                  </div>
                </div>
              </section>

              {/* Quick Features Overview */}
              <section className="quick-features-section">
                <h2 className="section-title">Was macht Liara besonders?</h2>
                <div className="quick-features-grid">
                  <NavLink to="/features" className="quick-feature-card">
                    <div className="quick-feature-icon">✨</div>
                    <h3>Features entdecken</h3>
                    <p>4D Memory, Sentiment-Analyse, Tasks, Kalender und mehr</p>
                    <span className="feature-arrow">→</span>
                  </NavLink>

                  <NavLink to="/privacy" className="quick-feature-card">
                    <div className="quick-feature-icon">🕵️</div>
                    <h3>Secure Data Network</h3>
                    <p>Deine Daten sind sicherer als in einem Tresor – DSGVO, lokal, keine Cloud</p>
                    <span className="feature-arrow">→</span>
                  </NavLink>

                  <NavLink to="/technology" className="quick-feature-card">
                    <div className="quick-feature-icon">🤖</div>
                    <h3>Technologie</h3>
                    <p>FastAPI, React, PostgreSQL, Neo4j, Ollama</p>
                    <span className="feature-arrow">→</span>
                  </NavLink>
                </div>
              </section>

              {/* Trust Badges */}
              <section className="social-proof-section">
                <div className="trust-badges">
                  <div className="trust-badge">
                    <div className="badge-icon">🔒</div>
                    <div className="badge-text">
                      <strong>100% Privacy</strong>
                      <span>Alle Daten lokal</span>
                    </div>
                  </div>
                  
                  <div className="trust-badge">
                    <div className="badge-icon">🏠</div>
                    <div className="badge-text">
                      <strong>Self-Hosted</strong>
                      <span>Keine Cloud nötig</span>
                    </div>
                  </div>
                  
                  <div className="trust-badge">
                    <div className="badge-icon">⚖️</div>
                    <div className="badge-text">
                      <strong>Open Source</strong>
                      <span>MIT License</span>
                    </div>
                  </div>
                  
                  <div className="trust-badge">
                    <div className="badge-icon">🇪🇺</div>
                    <div className="badge-text">
                      <strong>DSGVO</strong>
                      <span>Konform</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* Guest Chat Toggle Button */}
              {guestModeEnabled && (
                <button 
                  className="guest-chat-toggle"
                  onClick={() => setShowGuestChat(!showGuestChat)}
                  title="Gast-Chat öffnen"
                >
                  💬 Teste Liara jetzt
                </button>
              )}
            </>
          )}
        </div>
      </PageLayout>

    {/* Guest Chat Overlay Window - Outside PageLayout */}
    {guestModeEnabled && showGuestChat && (
      <div 
          className="guest-chat-overlay"
          style={{
            left: `${chatPosition.x}px`,
            top: `${chatPosition.y}px`
          }}
        >
          <div className="guest-chat-window">
            <div 
              className="guest-chat-header-overlay" 
              style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
              onMouseDown={handleMouseDown}
            >
              <div className="header-left">
                <span className="guest-chat-icon">🌙</span>
                <span className="guest-chat-title">Gast-Chat</span>
              </div>
              <div className="header-right">
                <span className="guest-chat-badge">20 Nachrichten</span>
                <button 
                  className="close-button"
                  onClick={() => setShowGuestChat(false)}
                  title="Schließen"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div className="guest-chat-messages-overlay">
              {guestMessages.map((msg, index) => (
                <div key={index} className={`guest-message guest-message-${msg.role}`}>
                  {msg.role === 'assistant' && <span className="message-avatar">🌙</span>}
                  {msg.role === 'user' && <span className="message-avatar">👤</span>}
                  <div className="message-content">{msg.content}</div>
                </div>
              ))}
              {guestLoading && (
                <div className="guest-message guest-message-assistant">
                  <span className="message-avatar">🌙</span>
                  <div className="message-content typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleGuestMessage} className="guest-chat-input-overlay">
              <input
                type="text"
                value={guestInput}
                onChange={(e) => setGuestInput(e.target.value)}
                placeholder="Nachricht..."
                maxLength={500}
                disabled={guestLoading || !guestModeEnabled}
              />
              <button type="submit" disabled={guestLoading || !guestInput.trim()}>
                ➤
              </button>
            </form>
            
            <p className="guest-chat-hint-overlay">
              💡 20 Nachrichten Limit • <strong>Registrieren</strong> für mehr
            </p>
          </div>
        </div>
      )
    }
    </>
  );
}

export default LandingPage;
