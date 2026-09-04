import { useState, useEffect } from 'react';
import './SystemConfig.css';
import './AgentProfiles.css';

function AgentProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchProfiles();
    fetchModels();
  }, []);

  const authHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
  });

  const fetchProfiles = async () => {
    try {
      const response = await fetch('/api/admin/agent-profiles', {
        headers: authHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setProfiles(data);
      const nextDrafts = {};
      data.forEach(profile => {
        nextDrafts[profile.id] = {
          name: profile.name,
          description: profile.description,
          default_model: profile.default_model,
          icon: profile.icon,
          category: profile.category,
        };
      });
      setDrafts(nextDrafts);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch agent profiles:', error);
      setMessage({ type: 'error', text: 'Fehler beim Laden der Agenten-Profile.' });
      setLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await fetch('/api/chat/models', {
        headers: authHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Failed to fetch models:', error);
    }
  };

  const updateDraft = (agentId, field, value) => {
    setDrafts(prev => ({
      ...prev,
      [agentId]: {
        ...prev[agentId],
        [field]: value
      }
    }));
  };

  const handleSave = async (agentId) => {
    setSavingId(agentId);
    setMessage(null);
    try {
      const response = await fetch(`/api/admin/agent-profiles/${agentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders()
        },
        body: JSON.stringify(drafts[agentId])
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const updated = await response.json();
      setProfiles(prev => prev.map(p => p.id === agentId ? updated : p));
      setMessage({ type: 'success', text: `${updated.name} gespeichert.` });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('Save error:', error);
      setMessage({ type: 'error', text: 'Fehler beim Speichern des Agenten-Profils.' });
    } finally {
      setSavingId(null);
    }
  };

  const handleReset = async (agentId) => {
    setSavingId(agentId);
    setMessage(null);
    try {
      const response = await fetch(`/api/admin/agent-profiles/${agentId}/reset`, {
        method: 'POST',
        headers: authHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const reset = await response.json();
      setProfiles(prev => prev.map(p => p.id === agentId ? reset : p));
      setDrafts(prev => ({
        ...prev,
        [agentId]: {
          name: reset.name,
          description: reset.description,
          default_model: reset.default_model,
          icon: reset.icon,
          category: reset.category,
        }
      }));
      setMessage({ type: 'success', text: `${reset.name} auf Standard zurückgesetzt.` });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('Reset error:', error);
      setMessage({ type: 'error', text: 'Fehler beim Zurücksetzen des Agenten-Profils.' });
    } finally {
      setSavingId(null);
    }
  };

  if (loading) {
    return (
      <div className="system-config">
        <div className="loading-state">
          <div className="loading-dots"><span></span><span></span><span></span></div>
          <p className="halo-mono">Lade Agenten-Profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="system-config">
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--color-text)' }}>
            🤖 Agenten-Profile
          </h1>
          <p className="halo-mono" style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            Name, Beschreibung, Standardmodell, Icon und Kategorie der spezialisierten Agenten anpassen
          </p>
        </div>
      </div>

      {message && (
        <div className={`message-banner ${message.type}`}>
          <span>{message.type === 'success' ? '✅' : '❌'}</span>
          <span>{message.text}</span>
        </div>
      )}

      <div className="agent-profiles-grid">
        {profiles.map(profile => {
          const draft = drafts[profile.id] || {};
          const busy = savingId === profile.id;
          return (
            <div key={profile.id} className="config-section halo-panel agent-profile-card">
              <div className="agent-profile-card-header">
                <h2 className="section-title halo-header" style={{ marginBottom: 0, border: 'none', paddingBottom: 0 }}>
                  {draft.icon || profile.icon} {profile.name}
                </h2>
                <span className={`agent-profile-badge ${profile.is_overridden ? 'customized' : 'default'}`}>
                  {profile.is_overridden ? 'Angepasst' : 'Standard'}
                </span>
              </div>

              <div className="config-grid">
                <div className="config-item">
                  <label className="config-label halo-mono">Name</label>
                  <input
                    type="text"
                    value={draft.name || ''}
                    onChange={(e) => updateDraft(profile.id, 'name', e.target.value)}
                    className="config-input"
                  />
                </div>

                <div className="config-item">
                  <label className="config-label halo-mono">Icon</label>
                  <input
                    type="text"
                    value={draft.icon || ''}
                    onChange={(e) => updateDraft(profile.id, 'icon', e.target.value)}
                    className="config-input"
                    maxLength="4"
                  />
                </div>

                <div className="config-item">
                  <label className="config-label halo-mono">Kategorie</label>
                  <input
                    type="text"
                    value={draft.category || ''}
                    onChange={(e) => updateDraft(profile.id, 'category', e.target.value)}
                    className="config-input"
                  />
                </div>

                <div className="config-item">
                  <label className="config-label halo-mono">Standardmodell</label>
                  <select
                    value={draft.default_model || ''}
                    onChange={(e) => updateDraft(profile.id, 'default_model', e.target.value)}
                    className="config-input"
                  >
                    {!models.find(m => m.name === draft.default_model) && draft.default_model && (
                      <option value={draft.default_model}>{draft.default_model}</option>
                    )}
                    {models.map(model => (
                      <option key={model.name} value={model.name}>
                        {model.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="config-item full-width">
                  <label className="config-label halo-mono">Beschreibung</label>
                  <textarea
                    value={draft.description || ''}
                    onChange={(e) => updateDraft(profile.id, 'description', e.target.value)}
                    className="config-textarea"
                    rows="3"
                  />
                </div>

                <div className="config-item full-width">
                  <label className="config-label halo-mono">Tools (im Code definiert, nicht editierbar)</label>
                  <div className="agent-profile-tools">
                    {profile.tools.map(tool => (
                      <span key={tool} className="agent-profile-tool-chip">{tool}</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="config-actions" style={{ paddingTop: 'var(--space-lg)' }}>
                <button
                  onClick={() => handleSave(profile.id)}
                  className="halo-button primary"
                  disabled={busy}
                >
                  {busy ? '💾 Speichere...' : '💾 Speichern'}
                </button>
                <button
                  onClick={() => handleReset(profile.id)}
                  className="halo-button secondary"
                  disabled={busy || !profile.is_overridden}
                >
                  🔄 Auf Standard zurücksetzen
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default AgentProfiles;
