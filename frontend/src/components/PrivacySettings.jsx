import { useState, useEffect } from 'react'
import { 
  getPrivacySettings, 
  updatePrivacySettings, 
  getLocationConsent,
  grantLocationConsent,
  revokeLocationConsent,
  exportUserData,
  deleteAllUserData
} from '../services/privacyService'
import PrivacyConsentModal from './PrivacyConsentModal'
import './PrivacySettings.css'
import './SettingsSection.css'

/**
 * Privacy Settings Page (User Settings Version)
 * 
 * DSGVO-konforme Privacy-Einstellungen:
 * - Location Tracking Consent
 * - Web Search History
 * - Auto-Delete Settings
 * - Data Export & Deletion
 */
function PrivacySettings() {
  const [settings, setSettings] = useState(null)
  const [locationData, setLocationData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showConsentModal, setShowConsentModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [locationRevokeConfirm, setLocationRevokeConfirm] = useState(false)
  const [deleteAllConfirm, setDeleteAllConfirm] = useState(false)
  const [deletingAll, setDeletingAll] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const [privacySettings, locationConsent] = await Promise.all([
        getPrivacySettings(),
        getLocationConsent()
      ])
      setSettings(privacySettings)
      setLocationData(locationConsent)
    } catch (error) {
      console.error('Failed to load privacy settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLocationToggle = () => {
    if (locationData?.consent_given) {
      setLocationRevokeConfirm(true)
    } else {
      // Show consent modal
      setShowConsentModal(true)
    }
  }

  const confirmRevokeLocation = async () => {
    setLocationRevokeConfirm(false)
    try {
      setSaving(true)
      await revokeLocationConsent()
      await loadSettings()
    } catch (error) {
      setErrorMessage('Fehler beim Widerrufen: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleConsentAccept = async () => {
    try {
      await grantLocationConsent()
      setShowConsentModal(false)
      await loadSettings()
    } catch (error) {
      setErrorMessage('Fehler bei der Standort-Erkennung: ' + error.message)
      throw error
    }
  }

  const handleConsentDecline = () => {
    setShowConsentModal(false)
  }

  const handleSearchHistoryToggle = async () => {
    try {
      setSaving(true)
      const newValue = !settings.web_search_history
      await updatePrivacySettings({ web_search_history: newValue })
      setSettings({ ...settings, web_search_history: newValue })
    } catch (error) {
      setErrorMessage('Fehler beim Speichern: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleAutoDeleteChange = async (days) => {
    try {
      setSaving(true)
      await updatePrivacySettings({ auto_delete_days: parseInt(days) })
      setSettings({ ...settings, auto_delete_days: parseInt(days) })
    } catch (error) {
      setErrorMessage('Fehler beim Speichern: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleExportData = async () => {
    try {
      const data = await exportUserData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `liara-data-export-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setErrorMessage('Fehler beim Daten-Export: ' + error.message)
    }
  }

  const handleDeleteAllData = () => {
    setDeleteAllConfirm(true)
  }

  const confirmDeleteAllData = async () => {
    setDeleteAllConfirm(false)
    setDeletingAll(true)
    try {
      await deleteAllUserData()
      setSuccessMessage('Alle Daten wurden erfolgreich gelöscht.')
      await loadSettings()
    } catch (error) {
      setErrorMessage('Fehler beim Löschen: ' + error.message)
    } finally {
      setDeletingAll(false)
    }
  }

  if (loading) {
    return (
      <div className="privacy-settings">
        <div className="privacy-loading">
          <div className="spinner"></div>
          <p>Lade Einstellungen...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="privacy-settings">
      <div className="privacy-header">
        <h1>🔒 Privacy-Einstellungen</h1>
        <p className="privacy-description">
          Verwalte deine Privatsphäre-Einstellungen. Alle Daten werden DSGVO-konform behandelt.
        </p>
      </div>

      {errorMessage && (
        <div className="settings-message error" onClick={() => setErrorMessage('')} style={{ cursor: 'pointer' }}>
          <span>⚠</span>
          <span>{errorMessage}</span>
        </div>
      )}
      {successMessage && (
        <div className="settings-message success" onClick={() => setSuccessMessage('')} style={{ cursor: 'pointer' }}>
          <span>✓</span>
          <span>{successMessage}</span>
        </div>
      )}

      {/* Location Tracking */}
      <div className="privacy-section">
        <div className="privacy-section-header">
          <h2>📍 Standort-Erkennung</h2>
        </div>
        
        <div className="privacy-setting">
          <div className="setting-info">
            <h3>Standort-Tracking</h3>
            <p>Ermöglicht lokale Informationen wie Wetter und News</p>
            {locationData?.consent_given && locationData.location && (
              <div className="current-location">
                <strong>Aktueller Standort:</strong>{' '}
                {locationData.location.city}, {locationData.location.region}, {locationData.location.country}
                <br />
                <span className="location-timezone">Zeitzone: {locationData.location.timezone}</span>
              </div>
            )}
          </div>
          <button
            className={`toggle-btn ${locationData?.consent_given ? 'active' : ''}`}
            onClick={handleLocationToggle}
            disabled={saving}
          >
            {locationData?.consent_given ? '✅ Aktiviert' : '❌ Deaktiviert'}
          </button>
        </div>

        <div className="privacy-note">
          <p>ℹ️ <strong>Privacy-Info:</strong> Wir speichern nur Stadt, Region und Land. 
          Keine IP-Adressen, kein GPS, keine Bewegungsprofile.</p>
        </div>
      </div>

      {/* Web Search History */}
      <div className="privacy-section">
        <div className="privacy-section-header">
          <h2>🔍 Web-Suchen</h2>
        </div>
        
        <div className="privacy-setting">
          <div className="setting-info">
            <h3>Suchverlauf speichern</h3>
            <p>Speichert Web-Suchen für bessere Ergebnisse und Personalisierung</p>
          </div>
          <button
            className={`toggle-btn ${settings?.web_search_history ? 'active' : ''}`}
            onClick={handleSearchHistoryToggle}
            disabled={saving}
          >
            {settings?.web_search_history ? '✅ Aktiviert' : '❌ Deaktiviert'}
          </button>
        </div>
      </div>

      {/* Auto-Delete */}
      <div className="privacy-section">
        <div className="privacy-section-header">
          <h2>🗑️ Automatische Löschung</h2>
        </div>
        
        <div className="privacy-setting">
          <div className="setting-info">
            <h3 id="auto-delete-label">Daten automatisch löschen nach</h3>
            <p>Alte Daten werden automatisch gelöscht (Standort, Suchen)</p>
          </div>
          <select
            className="auto-delete-select"
            value={settings?.auto_delete_days || 30}
            onChange={(e) => handleAutoDeleteChange(e.target.value)}
            disabled={saving}
            aria-labelledby="auto-delete-label"
            title="Zeitraum für automatische Datenlöschung"
          >
            <option value="0">Nie löschen</option>
            <option value="7">7 Tagen</option>
            <option value="14">14 Tagen</option>
            <option value="30">30 Tagen</option>
            <option value="90">90 Tagen</option>
            <option value="365">1 Jahr</option>
          </select>
        </div>
      </div>

      {/* GDPR Rights */}
      <div className="privacy-section danger">
        <div className="privacy-section-header">
          <h2>⚖️ Deine Rechte (DSGVO)</h2>
        </div>
        
        <div className="privacy-actions">
          <button className="btn-export" onClick={handleExportData}>
            📥 Daten exportieren
            <span className="btn-subtitle">Alle Daten als JSON herunterladen</span>
          </button>
          
          <button className="btn-delete-all" onClick={handleDeleteAllData} disabled={deletingAll}>
            🗑️ {deletingAll ? 'Lösche...' : 'Alle Daten löschen'}
            <span className="btn-subtitle">Recht auf Vergessenwerden (NICHT rückgängig!)</span>
          </button>
        </div>

        <div className="privacy-note">
          <p>🇪🇺 <strong>DSGVO-Konform:</strong> Du hast jederzeit das Recht auf Auskunft, 
          Berichtigung und Löschung deiner Daten. Alle Anfragen werden innerhalb von 30 Tagen bearbeitet.</p>
        </div>
      </div>

      {/* Legal Footer */}
      <div className="privacy-footer">
        <p>
          🔒 Alle Daten werden verschlüsselt auf EU-Servern gespeichert<br />
          📜 Weitere Informationen in unserer <a href="#">Datenschutzerklärung</a>
        </p>
      </div>

      {/* Consent Modal */}
      {showConsentModal && (
        <PrivacyConsentModal
          onAccept={handleConsentAccept}
          onDecline={handleConsentDecline}
        />
      )}

      {/* Revoke Location Consent Confirmation - not window.confirm(), which
          some browsers silently suppress after repeated dialogs */}
      {locationRevokeConfirm && (
        <div className="prefs-modal-overlay" onClick={() => setLocationRevokeConfirm(false)}>
          <div className="prefs-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Standort-Daten löschen?</h3>
            <p>Diese Aktion kann nicht rückgängig gemacht werden.</p>
            <div className="prefs-modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setLocationRevokeConfirm(false)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmRevokeLocation}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Data Confirmation - previously a chained double
          window.confirm(), which is exactly the fragile pattern this
          project replaces everywhere else with a single explicit modal */}
      {deleteAllConfirm && (
        <div className="prefs-modal-overlay" onClick={() => setDeleteAllConfirm(false)}>
          <div className="prefs-modal" onClick={(e) => e.stopPropagation()}>
            <h3>⚠️ Alle Daten wirklich löschen?</h3>
            <p>
              Dies umfasst Standort-Daten, Web-Suchen, Chat-Verlauf sowie Aufgaben, Notizen und Termine.
              Diese Aktion kann <strong>NICHT</strong> rückgängig gemacht werden!
            </p>
            <div className="prefs-modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setDeleteAllConfirm(false)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDeleteAllData}>
                Endgültig löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PrivacySettings
