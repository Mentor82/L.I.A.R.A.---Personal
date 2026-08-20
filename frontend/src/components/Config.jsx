import { useState, useEffect } from 'react';
import './Config.css';

function Config() {
  const [persona, setPersona] = useState(null);
  const [models, setModels] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConfigData();
    const interval = setInterval(loadConfigData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadConfigData = async () => {
    try {
      const [personaRes, modelsRes, infoRes, healthRes] = await Promise.all([
        fetch('/api/liara/persona'),
        fetch('/api/chat/models'),
        fetch('/api/info'),
        fetch('/api/chat/health')
      ]);

      const personaData = await personaRes.json();
      const modelsData = await modelsRes.json();
      const infoData = await infoRes.json();
      const healthData = await healthRes.json();

      console.log('Config data loaded:', { personaData, modelsData, infoData, healthData });

      setPersona(personaData);
      setModels(modelsData.models || []); // Extract models array
      setSystemInfo(infoData);
      setHealth(healthData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load config data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="config-loading">Loading configuration...</div>;
  }

  return (
    <div className="config-container">
      {/* Persona Section */}
      <section className="config-section persona-section">
        <h2>🌙 Persona</h2>
        {persona && (
          <div className="persona-card">
            <div className="persona-header">
              <h3>{persona.name}</h3>
              <span className="persona-version">v{persona.version}</span>
            </div>
            <p className="persona-tagline">{persona.tagline}</p>
            
            <div className="persona-traits">
              <h4>Core Traits</h4>
              <div className="traits-grid">
                {persona.tone?.primary?.map((trait) => {
                  const value = persona.current_state?.active_trait_modifiers?.[trait] || 0.5;
                  return (
                    <div key={trait} className="trait-item">
                      <span className="trait-name">{trait}</span>
                      <div className="trait-bar">
                        <div 
                          className="trait-fill" 
                          style={{ width: `${value * 100}%` }}
                        />
                      </div>
                      <span className="trait-value">{(value * 100).toFixed(0)}%</span>
                    </div>
                  );
                }) || <p>No traits available</p>}
              </div>
            </div>

            <div className="persona-communication">
              <h4>Communication Style</h4>
              <ul>
                {persona.tone?.description ? (
                  <li>{persona.tone.description}</li>
                ) : (
                  <li>No description available</li>
                )}
              </ul>
            </div>

            {persona.current_state && (
              <div className="persona-mood">
                <h4>Current Mood</h4>
                <div className="mood-display">
                  <span className="mood-emoji">{getMoodEmoji(persona.current_state.mood)}</span>
                  <span className="mood-name">{persona.current_state.mood}</span>
                  <span className="mood-intensity">
                    Intensity: {(persona.current_state.mood_intensity * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Models Section */}
      <section className="config-section models-section">
        <h2>🤖 Available Models</h2>
        <div className="models-grid">
          {models.map((model, idx) => (
            <div key={idx} className="model-card">
              <div className="model-header">
                <h3>{model.name}</h3>
                <div className="model-badges">
                  {model.gpu_support && <span className="badge gpu">GPU</span>}
                  {model.quality && (
                    <span className="badge quality">{model.quality}</span>
                  )}
                </div>
              </div>
              
              <div className="model-stats">
                <div className="stat">
                  <span className="stat-label">Speed</span>
                  <span className="stat-value">{model.speed || 'N/A'}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">RAM</span>
                  <span className="stat-value">{model.ram_required || 'N/A'}</span>
                </div>
              </div>

              {model.tags && model.tags.length > 0 && (
                <div className="model-tags">
                  {model.tags.map((tag, i) => (
                    <span key={i} className="tag">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* System Info Section */}
      <section className="config-section system-section">
        <h2>💻 System Information</h2>
        {systemInfo && (
          <div className="system-card">
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Hostname</span>
                <span className="info-value">{systemInfo.hostname}</span>
              </div>
              <div className="info-item">
                <span className="info-label">OS</span>
                <span className="info-value">{systemInfo.os}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Kernel</span>
                <span className="info-value">{systemInfo.kernel}</span>
              </div>
              <div className="info-item">
                <span className="info-label">CPU Cores</span>
                <span className="info-value">{systemInfo.cpu_count}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Uptime</span>
                <span className="info-value">{formatUptime(systemInfo.uptime)}</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Health Status Section */}
      <section className="config-section health-section">
        <h2>🏥 Health Status</h2>
        {health && (
          <div className="health-card">
            <div className={`health-indicator ${health.status}`}>
              <span className="health-light">●</span>
              <span className="health-text">{health.status.toUpperCase()}</span>
            </div>

            {health.components?.memory_system && (
              <div className="health-details">
                <h4>Memory System</h4>
                <div className="memory-stats">
                  <div className="stat">
                    <span className="stat-label">Messages</span>
                    <span className="stat-value">{health.components.memory_system.messages_stored}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Capacity</span>
                    <span className="stat-value">{(health.components.memory_system.capacity_used * 100).toFixed(1)}%</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Status</span>
                    <span className="stat-value">{health.components.memory_system.available ? '✓ OK' : '✗ Error'}</span>
                  </div>
                </div>
              </div>
            )}

            {health.components?.ollama && (
              <div className="health-details">
                <h4>Services</h4>
                <div className="service-status">
                  <span className={health.components.ollama.available ? 'status-ok' : 'status-error'}>
                    Ollama: {health.components.ollama.available ? `✓ Online (${health.components.ollama.models_loaded} models)` : '✗ Offline'}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

// Helper functions
function getMoodEmoji(mood) {
  const moodEmojis = {
    happy: '😊',
    focused: '🎯',
    curious: '🤔',
    helpful: '🤝',
    playful: '😄',
    neutral: '😌',
    concerned: '😟'
  };
  return moodEmojis[mood] || '😌';
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default Config;
