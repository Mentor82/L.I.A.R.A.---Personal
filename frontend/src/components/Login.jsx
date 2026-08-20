import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import './Login.css';

function Login({ onLogin }) {
  const location = useLocation();
  const [isRegister, setIsRegister] = useState(location.state?.register || false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    full_name: '',
    phone: '',
    date_of_birth: '',
    newsletter_opt_in: false,
    privacy_accepted: true
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [guestModeEnabled, setGuestModeEnabled] = useState(false);
  
  // Lade System Config beim Mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('/api/admin/config');
        if (response.ok) {
          const data = await response.json();
          setGuestModeEnabled(data.guest_mode_enabled === true);
        } else {
          // Fallback: Wenn Config nicht geladen werden kann, erlaube Guest-Mode
          setGuestModeEnabled(true);
        }
      } catch (error) {
        console.error('Error loading config:', error);
        // Fallback: Bei Fehler erlaube Guest-Mode
        setGuestModeEnabled(true);
      }
    };
    
    fetchConfig();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = isRegister ? '/auth/register' : '/auth/login';
      
      let body;
      if (isRegister) {
        // Build registration body with only non-empty values
        body = {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          privacy_accepted: formData.privacy_accepted
        };
        
        // Add optional fields only if they have values
        if (formData.phone && formData.phone.trim()) {
          body.phone = formData.phone;
        }
        if (formData.date_of_birth) {
          // Convert date to ISO datetime string
          body.date_of_birth = new Date(formData.date_of_birth).toISOString();
        }
        if (formData.newsletter_opt_in) {
          body.newsletter_opt_in = formData.newsletter_opt_in;
        }
      } else {
        body = { username: formData.username, password: formData.password };
      }
      
      console.log('Sending to:', `/api${endpoint}`);
      console.log('Request body:', body);

      const response = await fetch(`/api${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      console.log('Response status:', response.status);
      const data = await response.json();
      console.log('Response data:', data);

      if (!response.ok) {
        // Handle detail which could be string, array, or object
        let errorMsg = 'Anmeldung fehlgeschlagen';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(e => e.msg || e).join(', ');
          } else if (typeof data.detail === 'object') {
            errorMsg = JSON.stringify(data.detail);
          }
        }
        throw new Error(errorMsg);
      }

      // Store token and user info
      localStorage.setItem('liara_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('liara_refresh_token', data.refresh_token);
      }
      localStorage.setItem('liara_user', JSON.stringify(data.user));

      // Call parent callback
      onLogin(data.user);

    } catch (err) {
      // Handle error properly - could be string or object
      const errorMessage = typeof err === 'string' 
        ? err 
        : err.message || JSON.stringify(err) || 'Ein Fehler ist aufgetreten';
      setError(errorMessage);
      console.error('Login/Register Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGuestMode = () => {
    // Guest mode: fake user object without auth
    const guestUser = {
      username: 'guest',
      full_name: 'Gast',
      role: 'guest',
      is_guest: true
    };
    
    localStorage.setItem('liara_guest_mode', 'true');
    onLogin(guestUser);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>🌙 Liara</h1>
          <p>Deine persönliche Digitalbegleiterin</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <h2>{isRegister ? 'Registrierung' : 'Anmelden'}</h2>
          
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="username">Benutzername</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              autoFocus
              autoComplete="username"
              placeholder="Dein Benutzername"
              className="touch-optimized"
            />
          </div>

          {isRegister && (
            <>
              <div className="form-group">
                <label htmlFor="full_name">Vollständiger Name *</label>
                <input
                  type="text"
                  id="full_name"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  required
                  autoComplete="name"
                  placeholder="Max Mustermann"
                  className="touch-optimized"
                />
              </div>

              <div className="form-group">
                <label htmlFor="email">E-Mail *</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  autoComplete="email"
                  placeholder="deine@email.de"
                  className="touch-optimized"
                />
              </div>

              <div className="form-group">
                <label htmlFor="phone">Telefonnummer (optional)</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  autoComplete="tel"
                  placeholder="+49 123 456789"
                  className="touch-optimized"
                />
              </div>

              <div className="form-group">
                <label htmlFor="date_of_birth">Geburtsdatum (optional)</label>
                <input
                  type="date"
                  id="date_of_birth"
                  name="date_of_birth"
                  value={formData.date_of_birth}
                  onChange={handleChange}
                  className="touch-optimized"
                />
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    name="newsletter_opt_in"
                    checked={formData.newsletter_opt_in}
                    onChange={(e) => setFormData({...formData, newsletter_opt_in: e.target.checked})}
                  />
                  Newsletter abonnieren (optional)
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    name="privacy_accepted"
                    checked={formData.privacy_accepted}
                    onChange={(e) => setFormData({...formData, privacy_accepted: e.target.checked})}
                    required
                  />
                  Ich akzeptiere die <a href="/datenschutz" target="_blank">Datenschutzerklärung</a> *
                </label>
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="password">Passwort</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              autoComplete={isRegister ? "new-password" : "current-password"}
              placeholder="Dein Passwort"
              minLength={8}
              className="touch-optimized"
            />
          </div>

          <button 
            type="submit" 
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Einen Moment...' : (isRegister ? 'Registrieren' : 'Anmelden')}
          </button>

          <div className="toggle-mode">
            {isRegister ? (
              <p>
                Schon registriert?{' '}
                <button type="button" onClick={() => setIsRegister(false)}>
                  Hier anmelden
                </button>
              </p>
            ) : (
              <p>
                Noch kein Konto?{' '}
                <button type="button" onClick={() => setIsRegister(true)}>
                  Jetzt registrieren
                </button>
              </p>
            )}
          </div>

          {guestModeEnabled && (
            <>
              <div className="guest-mode-divider">
                <span>oder</span>
              </div>

              <button 
                type="button" 
                className="guest-mode-button"
                onClick={handleGuestMode}
              >
                👋 Als Gast reinschauen
              </button>
            </>
          )}
        </form>

        <div className="login-footer">
          <p className="info-text">
            🔒 Deine Daten bleiben lokal auf deinem Server
          </p>
          <p className="guest-info">
            💡 Im Gast-Modus kannst du Liara kennenlernen - mit eingeschränkten Funktionen
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
