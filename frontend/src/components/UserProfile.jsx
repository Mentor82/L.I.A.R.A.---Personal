import { useState, useEffect } from 'react'
import './SettingsSection.css'

function UserProfile() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(null)
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  useEffect(() => {
    const userData = localStorage.getItem('liara_user')
    if (userData) {
      const parsedUser = JSON.parse(userData)
      setUser(parsedUser)
      setFormData(prev => ({
        ...prev,
        full_name: parsedUser.full_name || '',
        email: parsedUser.email || ''
      }))
    }
    setLoading(false)
  }, [])

  const handleProfileUpdate = async (e) => {
    e.preventDefault()
    setMessage(null)

    try {
      const token = localStorage.getItem('liara_token')
      const updateData = {};
      if (formData.full_name) updateData.full_name = formData.full_name;
      if (formData.email) updateData.email = formData.email;
      
      const response = await fetch('/api/user/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(updateData)
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: 'Profil erfolgreich aktualisiert!' })
        localStorage.setItem('liara_user', JSON.stringify(data.user))
        setUser(data.user)
      } else {
        setMessage({ type: 'error', text: data.detail || 'Fehler beim Aktualisieren' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Netzwerkfehler' })
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    setMessage(null)

    if (formData.new_password !== formData.confirm_password) {
      setMessage({ type: 'error', text: 'Passwörter stimmen nicht überein' })
      return
    }

    if (formData.new_password.length < 6) {
      setMessage({ type: 'error', text: 'Passwort muss mindestens 6 Zeichen lang sein' })
      return
    }

    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/user/password', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: formData.current_password,
          new_password: formData.new_password
        })
      })

      const data = await response.json()

      if (response.ok) {
        setMessage({ type: 'success', text: 'Passwort erfolgreich geändert!' })
        setFormData(prev => ({
          ...prev,
          current_password: '',
          new_password: '',
          confirm_password: ''
        }))
      } else {
        setMessage({ type: 'error', text: data.detail || 'Fehler beim Ändern des Passworts' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Netzwerkfehler' })
    }
  }

  if (loading) {
    return <div className="loading-container"><div className="loading-spinner"></div></div>
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <h2 className="settings-section-title">👤 Profil-Informationen</h2>
        <p className="settings-section-desc">
          Verwalte deine persönlichen Informationen und Account-Details
        </p>
      </div>

      {message && (
        <div className={`settings-message ${message.type}`}>
          <span>{message.type === 'success' ? '✓' : '⚠'}</span>
          <span>{message.text}</span>
        </div>
      )}

      {/* Profile Info */}
      <div className="settings-card">
        <h3 className="settings-card-title">Persönliche Informationen</h3>
        <form onSubmit={handleProfileUpdate} className="settings-form">
          <div className="form-group">
            <label className="form-label">Benutzername</label>
            <input
              type="text"
              className="input"
              value={user?.username || ''}
              disabled
            />
            <span className="form-hint">Benutzername kann nicht geändert werden</span>
          </div>

          <div className="form-group">
            <label className="form-label">Vollständiger Name</label>
            <input
              type="text"
              className="input"
              value={formData.full_name}
              onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
              placeholder="Max Mustermann"
            />
          </div>

          <div className="form-group">
            <label className="form-label">E-Mail</label>
            <input
              type="email"
              className="input"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              placeholder="email@example.com"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Rolle</label>
            <div className="role-badge">
              {user?.role === 'admin' ? '🛡️ Administrator' : '👤 Benutzer'}
            </div>
          </div>

          <button type="submit" className="btn btn-primary">
            Profil speichern
          </button>
        </form>
      </div>

      {/* Password Change */}
      <div className="settings-card">
        <h3 className="settings-card-title">🔒 Passwort ändern</h3>
        <form onSubmit={handlePasswordChange} className="settings-form">
          <div className="form-group">
            <label className="form-label">Aktuelles Passwort</label>
            <input
              type="password"
              className="input"
              value={formData.current_password}
              onChange={(e) => setFormData(prev => ({ ...prev, current_password: e.target.value }))}
              placeholder="••••••••"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Neues Passwort</label>
            <input
              type="password"
              className="input"
              value={formData.new_password}
              onChange={(e) => setFormData(prev => ({ ...prev, new_password: e.target.value }))}
              placeholder="••••••••"
            />
            <span className="form-hint">Mindestens 6 Zeichen</span>
          </div>

          <div className="form-group">
            <label className="form-label">Passwort bestätigen</label>
            <input
              type="password"
              className="input"
              value={formData.confirm_password}
              onChange={(e) => setFormData(prev => ({ ...prev, confirm_password: e.target.value }))}
              placeholder="••••••••"
            />
          </div>

          <button type="submit" className="btn btn-primary">
            Passwort ändern
          </button>
        </form>
      </div>
    </div>
  )
}

export default UserProfile
