import { useState, useEffect } from 'react'
import { THEME_STORAGE_KEY, applyTheme } from '../utils/theme'
import './SettingsSection.css'

function UserPreferences() {
  const [preferences, setPreferences] = useState({
    ai_model: 'llama3.2:3b',
    language: 'de',
    theme: 'dark',
    notifications: true,
    sound_effects: false,
    custom_instructions: '',
    personality: 'warmherzig',
    memory_enabled: true,
    tool_memory_enabled: true,
    workspace_enabled: true
  })
  const [models, setModels] = useState([])
  const [personalityOptions, setPersonalityOptions] = useState([])
  const [personalityInsights, setPersonalityInsights] = useState(null)
  const [message, setMessage] = useState(null)
  const [memoriesToDelete, setMemoriesToDelete] = useState(false)
  const [deletingMemories, setDeletingMemories] = useState(false)

  useEffect(() => {
    loadPreferences()
    loadModels()
    loadPersonalityOptions()
    loadPersonalityInsights()
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
        setPreferences(prev => ({ ...prev, ...data, custom_instructions: data.custom_instructions || '' }))
      }
    } catch (error) {
      console.error('Failed to load preferences:', error)
    }
  }

  const loadModels = async () => {
    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/chat/models', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setModels(data.models || [])
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadPersonalityOptions = async () => {
    try {
      const response = await fetch('/api/user/preferences/personality-options')
      if (response.ok) {
        const data = await response.json()
        setPersonalityOptions(data.options || [])
      }
    } catch (error) {
      console.error('Failed to load personality options:', error)
    }
  }

  const loadPersonalityInsights = async () => {
    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/user/preferences/personality-insights', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setPersonalityInsights(await response.json())
      }
    } catch (error) {
      console.error('Failed to load personality insights:', error)
    }
  }

  const insightFor = (personalityValue) => {
    if (!personalityInsights) return null
    return personalityInsights.personalities.find(p => p.personality === personalityValue) || null
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
        
        // Update theme if changed - applyTheme() correctly resolves
        // "system" instead of writing it literally as data-theme (which
        // has no matching CSS selector and silently fell back to dark).
        if (preferences.theme) {
          localStorage.setItem(THEME_STORAGE_KEY, preferences.theme)
          applyTheme(preferences.theme)
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

  const confirmDeleteMemories = async () => {
    setMemoriesToDelete(false)
    setDeletingMemories(true)
    setMessage(null)

    try {
      const token = localStorage.getItem('liara_token')
      const response = await fetch('/api/user/memories?confirm=true', {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const data = await response.json()
        if (data.complete) {
          setMessage({ type: 'success', text: 'Erinnerungen wurden gelöscht.' })
        } else {
          // Partial deletion (e.g. Postgres cleared but Neo4j unreachable) -
          // safe to just try again, deleting an already-empty store is a no-op
          setMessage({ type: 'error', text: 'Erinnerungen wurden nur teilweise gelöscht. Bitte erneut versuchen.' })
        }
      } else {
        setMessage({ type: 'error', text: 'Fehler beim Löschen der Erinnerungen' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Netzwerkfehler' })
    } finally {
      setDeletingMemories(false)
    }
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
            {models.map(model => (
              <option key={model.name} value={model.name}>
                {model.name} {model.speed} {model.recommended ? '⭐' : ''}
              </option>
            ))}
          </select>
          <span className="form-hint">
            Wähle das AI-Modell für deine Chat-Konversationen
          </span>
        </div>
      </div>

      {/* Individuelle Anweisungen */}
      <div className="settings-card">
        <h3 className="settings-card-title">📝 Individuelle Anweisungen</h3>
        <div className="form-group">
          <textarea
            className="input"
            rows={4}
            maxLength={4000}
            placeholder="z.B. 'Antworte immer auf Deutsch und duze mich' oder 'Ich arbeite als Entwickler, erkläre technische Themen gerne detailliert'"
            value={preferences.custom_instructions}
            onChange={(e) => setPreferences(prev => ({ ...prev, custom_instructions: e.target.value }))}
          />
          <span className="form-hint">
            Diese Anweisungen werden in jedes Gespräch mit Liara eingebunden.
          </span>
        </div>
      </div>

      {/* Persönlichkeit */}
      <div className="settings-card">
        <h3 className="settings-card-title">🎭 Persönlichkeit</h3>
        <div className="personality-options">
          {personalityOptions.map(option => {
            const insight = insightFor(option.value)
            const isBest = personalityInsights?.best_personality === option.value
            return (
              <label
                key={option.value}
                className={`personality-option ${preferences.personality === option.value ? 'active' : ''}`}
              >
                <input
                  type="radio"
                  name="personality"
                  value={option.value}
                  checked={preferences.personality === option.value}
                  onChange={() => setPreferences(prev => ({ ...prev, personality: option.value }))}
                />
                <span className="personality-option-label">
                  {option.label}
                  {isBest && <span title="Wirkt bei dir bisher am besten"> ⭐</span>}
                </span>
                <span className="personality-option-desc">{option.description}</span>
                {insight && (
                  <span className="personality-option-insight">
                    Wirkung der Antwort: {insight.avg_score > 0 ? '+' : ''}{insight.avg_score} ({insight.sample_count} Antworten)
                  </span>
                )}
              </label>
            )
          })}
        </div>
        <span className="form-hint">
          Legt Liaras grundlegenden Kommunikationsstil fest, unabhängig von der automatischen Stimmung.
          {personalityInsights?.best_personality && ' ⭐ zeigt, welche Personality bisher am besten bei dir wirkt.'}
        </span>
      </div>

      {/* Wirkung nach Personality + Stimmung - feinere Aufschlüsselung als
          oben: welche Kombination in welcher Situation wirkt, statt nur
          "Personality X insgesamt am besten" */}
      {personalityInsights?.combinations?.some(c => c.sample_count >= personalityInsights.min_samples_required) && (
        <div className="settings-card">
          <h3 className="settings-card-title">🔍 Wirkung nach Situation</h3>
          <p className="form-hint" style={{ marginBottom: 'var(--space-sm)' }}>
            Manche Personality-Stimmungs-Kombinationen wirken besser als andere, je nach Situation.
          </p>
          <div className="personality-combo-list">
            {personalityInsights.combinations
              .filter(c => c.sample_count >= personalityInsights.min_samples_required)
              .slice(0, 5)
              .map((combo, idx) => {
                const label = personalityOptions.find(o => o.value === combo.personality)?.label || combo.personality
                const isBestCombo = personalityInsights.best_combination
                  && personalityInsights.best_combination.personality === combo.personality
                  && personalityInsights.best_combination.mood === combo.mood
                return (
                  <div key={idx} className="personality-combo-row">
                    <span>
                      {label} + {combo.mood}
                      {isBestCombo && <span title="Wirkt bei dir bisher am besten in dieser Situation"> ⭐</span>}
                    </span>
                    <span className="personality-option-insight">
                      {combo.avg_score > 0 ? '+' : ''}{combo.avg_score} ({combo.sample_count} Antworten)
                    </span>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      {/* Erinnerung */}
      <div className="settings-card">
        <h3 className="settings-card-title">🧠 Erinnerung</h3>

        <div className="switch-group">
          <div className="switch-label">
            <span className="switch-title">Erinnerungserstellung erlauben</span>
            <span className="switch-desc">
              Liara merkt sich Themen aus euren Gesprächen für zukünftigen Kontext
            </span>
          </div>
          <div
            className={`switch ${preferences.memory_enabled ? 'active' : ''}`}
            onClick={() => togglePreference('memory_enabled')}
          >
            <div className="switch-toggle"></div>
          </div>
        </div>

        <div className="switch-group">
          <div className="switch-label">
            <span className="switch-title">Erinnerungen aus toolgestützten Chats</span>
            <span className="switch-desc">
              Erinnerungen auch aus Chats erstellen, in denen Tools oder die Websuche genutzt wurden
            </span>
          </div>
          <div
            className={`switch ${preferences.tool_memory_enabled ? 'active' : ''} ${!preferences.memory_enabled ? 'disabled' : ''}`}
            onClick={() => preferences.memory_enabled && togglePreference('tool_memory_enabled')}
          >
            <div className="switch-toggle"></div>
          </div>
        </div>

        <button
          type="button"
          className="btn-danger"
          style={{ marginTop: 'var(--space-md)' }}
          onClick={() => setMemoriesToDelete(true)}
          disabled={deletingMemories}
        >
          {deletingMemories ? 'Lösche...' : '🗑️ Erinnerungen löschen'}
        </button>
      </div>

      {/* Workspace */}
      <div className="settings-card">
        <h3 className="settings-card-title">🗂️ Workspace</h3>

        <div className="switch-group">
          <div className="switch-label">
            <span className="switch-title">Workspace-Tab aktivieren</span>
            <span className="switch-desc">
              Gemeinsamer Datei-/Code-Bereich mit Editor, Ausführung und Artefakten - erscheint als eigener Hauptreiter
            </span>
          </div>
          <div
            className={`switch ${preferences.workspace_enabled ? 'active' : ''}`}
            onClick={() => togglePreference('workspace_enabled')}
          >
            <div className="switch-toggle"></div>
          </div>
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

      {/* Delete Memories Confirmation Modal - not window.confirm(), which
          some browsers silently suppress after repeated dialogs */}
      {memoriesToDelete && (
        <div className="prefs-modal-overlay" onClick={() => setMemoriesToDelete(false)}>
          <div className="prefs-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Erinnerungen löschen?</h3>
            <p>
              Alle von Liara gespeicherten Konzepte und Zusammenhänge aus euren Gesprächen werden
              unwiderruflich gelöscht. Deine Chat-Verläufe selbst bleiben davon unberührt.
            </p>
            <div className="prefs-modal-actions">
              <button type="button" className="btn-secondary" onClick={() => setMemoriesToDelete(false)}>
                Abbrechen
              </button>
              <button type="button" className="btn-danger" onClick={confirmDeleteMemories}>
                Löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserPreferences
