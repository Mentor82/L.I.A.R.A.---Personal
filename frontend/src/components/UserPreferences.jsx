import { useState, useEffect } from 'react'
import './SettingsSection.css'

function UserPreferences() {
  const [preferences, setPreferences] = useState({
    ai_model: 'llama3.2',
    language: 'de',
    theme: 'dark',
    notifications: true,
    sound_effects: false
  })
  const [message, setMessage] = useState(null)

  useEffect(() => {
    loadPreferences()
  }, [])

  const loadPreferences = async () => {
    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/user/preferences', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setPreferences(data)
      }
    } catch (error) {
      console.error('Failed to load preferences:', error)
    }
  }

  const savePreferences = async () => {
    setMessage(null)

    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/user/preferences', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(preferences)
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Präferenzen gespeichert!' })
        
        // Update theme if changed
        if (preferences.theme) {
          localStorage.setItem('liara_theme', preferences.theme)
          document.documentElement.setAttribute('data-theme', preferences.theme)
        }
      } else {
        setMessage({ type: 'error', text: 'Fehler beim Speichern' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Netzwerkfehler' })
    }
  }

  const togglePreference = (key) => {
    setPreferences(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2 className="settings-section-title">⚙️ Präferenzen</h2>
        <p className="settings-section-desc">
          Passe Liara an deine Bedürfnisse an
        </p>
      </div>

      {message && (
        <div className={`settings-message ${message.type}`}>
          <span>{message.type === 'success' ? '✓' : '⚠'}</span>
          <span>{message.text}</span>
        </div>
      )}

      {/* AI Model Selection */}
      <div className="settings-card">
        <h3 className="settings-card-title">🤖 AI-Modell</h3>
        <div className="form-group">
          <label className="form-label">Standard AI-Modell</label>
          <select
            className="input"
            value={preferences.ai_model}
            onChange={(e) => setPreferences(prev => ({ ...prev, ai_model: e.target.value }))}
          >
            <option value="llama3.2">Llama 3.2 (Schnell & Effizient)</option>
            <option value="qwen2.5:7b">Qwen 2.5 7B (Balanced)</option>
            <option value="qwen2.5:14b">Qwen 2.5 14B (Leistungsstark)</option>
            <option value="deepseek-r1:8b">DeepSeek R1 8B (Reasoning)</option>
            <option value="mistral">Mistral (Vielseitig)</option>
            <option value="codellama">Code Llama (Programmierung)</option>
          </select>
          <span className="form-hint">
            Wähle das AI-Modell für deine Chat-Konversationen
          </span>
        </div>
      </div>

      {/* Language & Theme */}
      <div className="settings-card">
        <h3 className="settings-card-title">🌐 Sprache & Aussehen</h3>
        
        <div className="form-group">
          <label className="form-label">Sprache</label>
          <select
            className="input"
            value={preferences.language}
            onChange={(e) => setPreferences(prev => ({ ...prev, language: e.target.value }))}
          >
            <option value="de">Deutsch</option>
            <option value="en">English</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Theme</label>
          <select
            className="input"
            value={preferences.theme}
            onChange={(e) => setPreferences(prev => ({ ...prev, theme: e.target.value }))}
          >
            <option value="dark">Dark Mode (Halo/UNSC)</option>
            <option value="light">Light Mode</option>
            <option value="system">System Preference</option>
          </select>
          <span className="form-hint">
            Wähle dein bevorzugtes Farbschema
          </span>
        </div>
      </div>

      {/* Notifications & Sound */}
      <div className="settings-card">
        <h3 className="settings-card-title">🔔 Benachrichtigungen & Sound</h3>
        
        <div className="switch-group">
          <div className="switch-label">
            <span className="switch-title">Benachrichtigungen</span>
            <span className="switch-desc">
              Erhalte Benachrichtigungen für wichtige Events
            </span>
          </div>
          <div 
            className={`switch ${preferences.notifications ? 'active' : ''}`}
            onClick={() => togglePreference('notifications')}
          >
            <div className="switch-toggle"></div>
          </div>
        </div>

        <div className="switch-group">
          <div className="switch-label">
            <span className="switch-title">Sound-Effekte</span>
            <span className="switch-desc">
              Spiele Sound-Effekte bei Aktionen
            </span>
          </div>
          <div 
            className={`switch ${preferences.sound_effects ? 'active' : ''}`}
            onClick={() => togglePreference('sound_effects')}
          >
            <div className="switch-toggle"></div>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="info-box">
        <span className="info-box-icon">💡</span>
        <div>
          <strong>Tipp:</strong> Deine Präferenzen werden automatisch mit deinem Account synchronisiert. 
          Du kannst sie jederzeit ändern.
        </div>
      </div>

      {/* Save Button */}
      <button onClick={savePreferences} className="btn btn-primary">
        Präferenzen speichern
      </button>
    </div>
  )
}

export default UserPreferences
