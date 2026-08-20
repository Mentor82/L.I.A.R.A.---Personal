import { useState, useEffect } from 'react';
import './SystemConfig.css';

function SystemConfig() {
  const [config, setConfig] = useState({
    system: {
      defaultModel: 'llama3.2:3b',
      maxTokens: 2000,
      temperature: 0.7,
      systemPrompt: '',
    },
    limits: {
      guestMessageLimit: 20,
      guestMessageLength: 500,
      userMessageLimit: 100,
      rateLimitWindow: 60,
    },
    features: {
      webSearchEnabled: true,
      locationServicesEnabled: true,
      guestModeEnabled: true,
      registrationEnabled: true,
    },
    privacy: {
      dataRetentionDays: 30,
      searchHistoryRetentionDays: 7,
      locationRetentionDays: 30,
      autoDeleteEnabled: true,
    },
    ollama: {
      host: 'http://localhost:11434',
      timeout: 120,
      pullOnStart: false,
    }
  });

  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchConfig();
    fetchModels();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/admin/config', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      
      // Konvertiere API-Response zu Frontend-Format
      setConfig({
        system: {
          defaultModel: data.default_model,
          maxTokens: data.max_tokens,
          temperature: data.temperature / 100,  // 0-100 zu 0.0-1.0
          systemPrompt: data.system_prompt || '',
        },
        limits: {
          guestMessageLimit: data.guest_message_limit,
          guestMessageLength: data.guest_message_length,
          userMessageLimit: data.user_message_limit,
          rateLimitWindow: data.rate_limit_window,
        },
        features: {
          webSearchEnabled: data.web_search_enabled,
          locationServicesEnabled: data.location_services_enabled,
          guestModeEnabled: data.guest_mode_enabled,
          registrationEnabled: data.registration_enabled,
        },
        privacy: {
          dataRetentionDays: data.data_retention_days,
          searchHistoryRetentionDays: data.search_history_retention_days,
          locationRetentionDays: data.location_retention_days,
          autoDeleteEnabled: data.auto_delete_enabled,
        },
        ollama: {
          host: data.ollama_host,
          timeout: data.ollama_timeout,
          pullOnStart: data.ollama_pull_on_start,
        }
      });
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch config:', error);
      setMessage({ type: 'error', text: 'Fehler beim Laden der Konfiguration.' });
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/chat/models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    
    try {
      // Konvertiere Frontend-Format zu API-Format
      const payload = {
        default_model: config.system.defaultModel,
        max_tokens: config.system.maxTokens,
        temperature: Math.round(config.system.temperature * 100),  // 0.0-1.0 zu 0-100
        system_prompt: config.system.systemPrompt || null,
        guest_message_limit: config.limits.guestMessageLimit,
        guest_message_length: config.limits.guestMessageLength,
        user_message_limit: config.limits.userMessageLimit,
        rate_limit_window: config.limits.rateLimitWindow,
        web_search_enabled: config.features.webSearchEnabled,
        location_services_enabled: config.features.locationServicesEnabled,
        guest_mode_enabled: config.features.guestModeEnabled,
        registration_enabled: config.features.registrationEnabled,
        data_retention_days: config.privacy.dataRetentionDays,
        search_history_retention_days: config.privacy.searchHistoryRetentionDays,
        location_retention_days: config.privacy.locationRetentionDays,
        auto_delete_enabled: config.privacy.autoDeleteEnabled,
        ollama_host: config.ollama.host,
        ollama_timeout: config.ollama.timeout,
        ollama_pull_on_start: config.ollama.pullOnStart,
      };
      
      const response = await fetch('/api/admin/config', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      setMessage({ type: 'success', text: 'Konfiguration erfolgreich gespeichert!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('Save error:', error);
      setMessage({ type: 'error', text: 'Fehler beim Speichern der Konfiguration.' });
    } finally {
      setSaving(false);
    }
  };

  const updateConfig = (section, key, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  if (loading) {
    return (
      <div className="system-config">
        <div className="loading-state">
          <div className="loading-dots"><span></span><span></span><span></span></div>
          <p className="halo-mono">Lade Konfiguration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="system-config">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--color-text)' }}>
            ⚙️ System-Konfiguration
          </h1>
          <p className="halo-mono" style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            Globale Einstellungen und Systemparameter
          </p>
        </div>
        <button 
          onClick={handleSave} 
          className="halo-button"
          disabled={saving}
        >
          {saving ? '💾 Speichere...' : '💾 Speichern'}
        </button>
      </div>

      {/* Message Banner */}
      {message && (
        <div className={`message-banner ${message.type}`}>
          <span>{message.type === 'success' ? '✅' : '❌'}</span>
          <span>{message.text}</span>
        </div>
      )}

      {/* AI & Model Settings */}
      <div className="config-section halo-panel">
        <h2 className="section-title halo-header">
          🤖 AI & Model Einstellungen
        </h2>
        
        <div className="config-grid">
          <div className="config-item">
            <label className="config-label halo-mono">Standard AI Model</label>
            <select
              value={config.system.defaultModel}
              onChange={(e) => updateConfig('system', 'defaultModel', e.target.value)}
              className="config-input"
            >
              {models.map(model => (
                <option key={model.name} value={model.name}>
                  {model.name} ({model.size})
                </option>
              ))}
            </select>
            <span className="config-hint">Model für neue Chat-Sitzungen</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Max Tokens</label>
            <input
              type="number"
              value={config.system.maxTokens}
              onChange={(e) => updateConfig('system', 'maxTokens', parseInt(e.target.value))}
              className="config-input"
              min="100"
              max="8000"
            />
            <span className="config-hint">Maximale Antwortlänge</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Temperature</label>
            <div className="slider-container">
              <input
                type="range"
                value={config.system.temperature}
                onChange={(e) => updateConfig('system', 'temperature', parseFloat(e.target.value))}
                min="0"
                max="1"
                step="0.1"
                className="config-slider"
              />
              <span className="slider-value">{config.system.temperature}</span>
            </div>
            <span className="config-hint">Kreativität (0 = präzise, 1 = kreativ)</span>
          </div>

          <div className="config-item full-width">
            <label className="config-label halo-mono">System Prompt (Optional)</label>
            <textarea
              value={config.system.systemPrompt}
              onChange={(e) => updateConfig('system', 'systemPrompt', e.target.value)}
              className="config-textarea"
              placeholder="Globaler System-Prompt für alle Chats..."
              rows="4"
            />
            <span className="config-hint">Wird allen Konversationen vorangestellt</span>
          </div>
        </div>
      </div>

      {/* Rate Limits */}
      <div className="config-section halo-panel">
        <h2 className="section-title halo-header">
          🚦 Rate Limits & Beschränkungen
        </h2>
        
        <div className="config-grid">
          <div className="config-item">
            <label className="config-label halo-mono">Gast: Nachrichten Limit</label>
            <input
              type="number"
              value={config.limits.guestMessageLimit}
              onChange={(e) => updateConfig('limits', 'guestMessageLimit', parseInt(e.target.value))}
              className="config-input"
              min="1"
              max="100"
            />
            <span className="config-hint">Max. Nachrichten im Gast-Modus</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Gast: Max. Zeichenlänge</label>
            <input
              type="number"
              value={config.limits.guestMessageLength}
              onChange={(e) => updateConfig('limits', 'guestMessageLength', parseInt(e.target.value))}
              className="config-input"
              min="100"
              max="2000"
            />
            <span className="config-hint">Max. Zeichen pro Gast-Nachricht</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">User: Nachrichten Limit</label>
            <input
              type="number"
              value={config.limits.userMessageLimit}
              onChange={(e) => updateConfig('limits', 'userMessageLimit', parseInt(e.target.value))}
              className="config-input"
              min="10"
              max="1000"
            />
            <span className="config-hint">Max. Nachrichten für registrierte User</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Rate Limit Fenster (Sekunden)</label>
            <input
              type="number"
              value={config.limits.rateLimitWindow}
              onChange={(e) => updateConfig('limits', 'rateLimitWindow', parseInt(e.target.value))}
              className="config-input"
              min="10"
              max="3600"
            />
            <span className="config-hint">Zeitfenster für Rate Limiting</span>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="config-section halo-panel">
        <h2 className="section-title halo-header">
          🎯 Features & Module
        </h2>
        
        <div className="features-grid">
          <div className="feature-toggle">
            <div className="feature-info">
              <div className="feature-name halo-mono">Web-Suche aktiviert</div>
              <div className="feature-desc">DuckDuckGo, Wikipedia, Weather API</div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={config.features.webSearchEnabled}
                onChange={(e) => updateConfig('features', 'webSearchEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <div className="feature-toggle">
            <div className="feature-info">
              <div className="feature-name halo-mono">Standort-Dienste</div>
              <div className="feature-desc">IP-basierte Lokalisierung</div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={config.features.locationServicesEnabled}
                onChange={(e) => updateConfig('features', 'locationServicesEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <div className="feature-toggle">
            <div className="feature-info">
              <div className="feature-name halo-mono">Gast-Modus</div>
              <div className="feature-desc">Chat ohne Registrierung</div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={config.features.guestModeEnabled}
                onChange={(e) => updateConfig('features', 'guestModeEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>

          <div className="feature-toggle">
            <div className="feature-info">
              <div className="feature-name halo-mono">Registrierung öffentlich</div>
              <div className="feature-desc">Neue User können sich anmelden</div>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={config.features.registrationEnabled}
                onChange={(e) => updateConfig('features', 'registrationEnabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* Privacy & Data Retention */}
      <div className="config-section halo-panel">
        <h2 className="section-title halo-header">
          🔒 Privacy & Datenspeicherung
        </h2>
        
        <div className="config-grid">
          <div className="config-item">
            <label className="config-label halo-mono">Chat-Daten behalten (Tage)</label>
            <input
              type="number"
              value={config.privacy.dataRetentionDays}
              onChange={(e) => updateConfig('privacy', 'dataRetentionDays', parseInt(e.target.value))}
              className="config-input"
              min="1"
              max="365"
            />
            <span className="config-hint">0 = unbegrenzt</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Such-Verlauf (Tage)</label>
            <input
              type="number"
              value={config.privacy.searchHistoryRetentionDays}
              onChange={(e) => updateConfig('privacy', 'searchHistoryRetentionDays', parseInt(e.target.value))}
              className="config-input"
              min="1"
              max="90"
            />
            <span className="config-hint">Web-Suchen automatisch löschen</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Standort-Daten (Tage)</label>
            <input
              type="number"
              value={config.privacy.locationRetentionDays}
              onChange={(e) => updateConfig('privacy', 'locationRetentionDays', parseInt(e.target.value))}
              className="config-input"
              min="1"
              max="90"
            />
            <span className="config-hint">IP-Lokalisierung löschen nach</span>
          </div>

          <div className="config-item">
            <div className="feature-toggle inline">
              <div className="feature-info">
                <div className="feature-name halo-mono">Auto-Delete aktiviert</div>
                <div className="feature-desc">Automatische Datenlöschung nach Ablauf</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={config.privacy.autoDeleteEnabled}
                  onChange={(e) => updateConfig('privacy', 'autoDeleteEnabled', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Ollama Configuration */}
      <div className="config-section halo-panel">
        <h2 className="section-title halo-header">
          🦙 Ollama Konfiguration
        </h2>
        
        <div className="config-grid">
          <div className="config-item">
            <label className="config-label halo-mono">Ollama Host</label>
            <input
              type="text"
              value={config.ollama.host}
              onChange={(e) => updateConfig('ollama', 'host', e.target.value)}
              className="config-input"
              placeholder="http://localhost:11434"
            />
            <span className="config-hint">Ollama API Endpunkt</span>
          </div>

          <div className="config-item">
            <label className="config-label halo-mono">Timeout (Sekunden)</label>
            <input
              type="number"
              value={config.ollama.timeout}
              onChange={(e) => updateConfig('ollama', 'timeout', parseInt(e.target.value))}
              className="config-input"
              min="30"
              max="600"
            />
            <span className="config-hint">Max. Wartezeit für Antworten</span>
          </div>

          <div className="config-item">
            <div className="feature-toggle inline">
              <div className="feature-info">
                <div className="feature-name halo-mono">Auto-Pull beim Start</div>
                <div className="feature-desc">Fehlende Models automatisch laden</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={config.ollama.pullOnStart}
                  onChange={(e) => updateConfig('ollama', 'pullOnStart', e.target.checked)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button (repeated at bottom) */}
      <div className="config-actions">
        <button 
          onClick={handleSave} 
          className="halo-button primary"
          disabled={saving}
        >
          {saving ? '💾 Speichere...' : '💾 Änderungen speichern'}
        </button>
        <button 
          onClick={fetchConfig} 
          className="halo-button secondary"
        >
          🔄 Zurücksetzen
        </button>
      </div>
    </div>
  );
}

export default SystemConfig;
