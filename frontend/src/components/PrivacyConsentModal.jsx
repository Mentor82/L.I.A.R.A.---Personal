import { useState } from 'react'
import './PrivacyConsentModal.css'

/**
 * Privacy Consent Modal für Location-Tracking
 * 
 * Zeigt Privacy-Informationen und fordert Consent an
 */
function PrivacyConsentModal({ onAccept, onDecline }) {
  const [loading, setLoading] = useState(false)

  const handleAccept = async () => {
    setLoading(true)
    try {
      await onAccept()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="privacy-modal-overlay">
      <div className="privacy-modal">
        <div className="privacy-modal-header">
          <h2>🔒 Standort-Erkennung</h2>
          <p className="privacy-subtitle">Deine Privatsphäre ist wichtig</p>
        </div>

        <div className="privacy-modal-content">
          <div className="privacy-info-box">
            <h3>📍 Was wird gespeichert?</h3>
            <ul>
              <li><strong>Stadt & Region</strong> – Für lokale Informationen (Wetter, News)</li>
              <li><strong>Zeitzone</strong> – Für korrekte Zeitanzeigen</li>
              <li><strong>Land</strong> – Für Sprache und lokale Services</li>
            </ul>
          </div>

          <div className="privacy-info-box warning">
            <h3>❌ Was wird NICHT gespeichert?</h3>
            <ul>
              <li><strong>Keine IP-Adresse</strong> – Wird nur zur Erkennung verwendet</li>
              <li><strong>Kein GPS</strong> – Nur Stadt-Level Genauigkeit</li>
              <li><strong>Kein Tracking</strong> – Keine Bewegungsprofile</li>
            </ul>
          </div>

          <div className="privacy-info-box success">
            <h3>✅ Deine Rechte</h3>
            <ul>
              <li><strong>Jederzeit widerrufbar</strong> – In den Privacy-Einstellungen</li>
              <li><strong>Sofortige Löschung</strong> – Alle Daten werden gelöscht</li>
              <li><strong>Auto-Delete</strong> – Nach 30 Tagen automatisch gelöscht</li>
            </ul>
          </div>

          <div className="privacy-example">
            <p><strong>Beispiel:</strong> "Wie ist das Wetter?" → Verwendet deinen Standort statt zu fragen</p>
          </div>
        </div>

        <div className="privacy-modal-footer">
          <button 
            className="btn-decline" 
            onClick={onDecline}
            disabled={loading}
          >
            ❌ Ablehnen
          </button>
          <button 
            className="btn-accept" 
            onClick={handleAccept}
            disabled={loading}
          >
            {loading ? '⏳ Erkenne Standort...' : '✅ Akzeptieren'}
          </button>
        </div>

        <div className="privacy-modal-legal">
          <p>🔒 DSGVO-konform | 🇪🇺 EU-Server | 🔐 Ende-zu-Ende verschlüsselt</p>
        </div>
      </div>
    </div>
  )
}

export default PrivacyConsentModal
