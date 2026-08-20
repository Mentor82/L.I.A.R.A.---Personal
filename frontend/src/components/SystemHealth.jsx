import { useState, useEffect } from 'react';
import './SystemHealth.css';

function SystemHealth() {
  const [health, setHealth] = useState(null);
  const [loadData, setLoadData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      
      // Parallel requests for health and load
      const [healthResponse, loadResponse] = await Promise.all([
        fetch('/api/admin/health/full', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
          }
        }),
        fetch('/api/system/load')
      ]);
      
      if (!healthResponse.ok) throw new Error(`HTTP ${healthResponse.status}`);
      const healthData = await healthResponse.json();
      setHealth(healthData);
      
      if (loadResponse.ok) {
        const load = await loadResponse.json();
        setLoadData(load);
      }
      
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    
    if (autoRefresh) {
      const interval = setInterval(fetchHealth, 30000); // 30 Sekunden
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'var(--halo-accent)';
      case 'warning': return 'var(--halo-warning)';
      case 'degraded': return 'var(--halo-warning)';
      case 'critical': return 'var(--halo-danger)';
      default: return 'var(--text-tertiary)';
    }
  };

  const getStatusIcon = (healthy) => {
    return healthy ? '✅' : '❌';
  };

  if (loading && !health) {
    return (
      <div className="system-health halo-bg-pattern">
        <div className="health-container halo-panel">
          <div className="loading-state">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p className="halo-mono">Scanning system components...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="system-health halo-bg-pattern">
        <div className="health-container halo-panel">
          <div className="error-state">
            <h2 className="halo-header" style={{ color: 'var(--halo-danger)' }}>
              System Check Failed
            </h2>
            <p className="legal-text">{error}</p>
            <button onClick={fetchHealth} className="halo-button">
              Retry Scan
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!health) return null;

  const { overall, system, services, ports, containers, databases, endpoints, ai_services } = health;

  return (
    <div className="system-health halo-bg-pattern">
      <div className="halo-scan-line"></div>
      
      <div className="health-container">
        {/* Header */}
        <div className="health-header halo-panel compact-spacing">
          <div>
            <h1 className="halo-header" style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
              🏥 System Health Diagnostics
            </h1>
            <p className="halo-mono" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Real-time monitoring • Liara Protocol
            </p>
          </div>
          <div className="health-controls">
            <label className="auto-refresh-toggle">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span className="halo-mono" style={{ fontSize: '0.75rem' }}>Auto-Refresh (30s)</span>
            </label>
            <button onClick={fetchHealth} className="halo-button" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}>
              🔄 Scan
            </button>
          </div>
        </div>

        {/* Overall Status */}
        <div className="health-overall halo-panel compact-spacing">
          <div className="overall-status">
            <div className="status-indicator" style={{ 
              background: `linear-gradient(135deg, ${getStatusColor(overall.status)}, transparent)`,
              borderColor: getStatusColor(overall.status),
              boxShadow: `0 0 20px ${getStatusColor(overall.status)}`
            }}>
              <div className="status-percentage" style={{ color: getStatusColor(overall.status) }}>
                {overall.health_percentage.toFixed(0)}%
              </div>
              <div className="status-label halo-mono">SYSTEM HEALTH</div>
            </div>
            <div className="status-details">
              <div className="status-item">
                <span className="halo-mono">Status:</span>
                <span className="halo-badge" style={{ 
                  borderColor: getStatusColor(overall.status),
                  color: getStatusColor(overall.status)
                }}>
                  {overall.status.toUpperCase()}
                </span>
              </div>
              <div className="status-item">
                <span className="halo-mono">Checks Passed:</span>
                <span className="halo-mono" style={{ color: 'var(--halo-primary)' }}>
                  {overall.checks_passed} / {overall.checks_total}
                </span>
              </div>
              <div className="status-item">
                <span className="halo-mono">Last Scan:</span>
                <span className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {new Date(health.timestamp).toLocaleTimeString('de-DE')}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time System Load */}
        {loadData && (
          <div className="health-section halo-panel compact-spacing">
            <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
              ⚡ Live System Load
            </h2>
            <div className="system-grid">
              <div className="system-card">
                <div className="card-header">
                  <span className="halo-mono">CPU Usage</span>
                  <span className="halo-badge" style={{ 
                    borderColor: loadData.cpu_percent > 70 ? 'var(--halo-danger)' : 'var(--halo-accent)',
                    color: loadData.cpu_percent > 70 ? 'var(--halo-danger)' : 'var(--halo-accent)'
                  }}>
                    {loadData.cpu_percent}%
                  </span>
                </div>
                <div className="progress-bar" style={{ marginTop: '0.5rem' }}>
                  <div className="progress-fill" style={{ 
                    width: `${loadData.cpu_percent}%`,
                    background: loadData.cpu_percent > 70 ? 'var(--halo-danger)' : 'var(--halo-accent)'
                  }}></div>
                </div>
              </div>

              <div className="system-card">
                <div className="card-header">
                  <span className="halo-mono">Memory Usage</span>
                  <span className="halo-badge" style={{ 
                    borderColor: loadData.memory_percent > 80 ? 'var(--halo-danger)' : 'var(--halo-accent)',
                    color: loadData.memory_percent > 80 ? 'var(--halo-danger)' : 'var(--halo-accent)'
                  }}>
                    {loadData.memory_percent}%
                  </span>
                </div>
                <div className="progress-bar" style={{ marginTop: '0.5rem' }}>
                  <div className="progress-fill" style={{ 
                    width: `${loadData.memory_percent}%`,
                    background: loadData.memory_percent > 80 ? 'var(--halo-danger)' : 'var(--halo-accent)'
                  }}></div>
                </div>
              </div>

              <div className="system-card">
                <div className="card-header">
                  <span className="halo-mono">SSE Mode</span>
                  <span className="halo-badge" style={{ 
                    borderColor: loadData.recommendation === 'sse' ? 'var(--halo-accent)' : 'var(--halo-warning)',
                    color: loadData.recommendation === 'sse' ? 'var(--halo-accent)' : 'var(--halo-warning)'
                  }}>
                    {loadData.recommendation === 'sse' ? '✓ Streaming' : '⚠ Sync'}
                  </span>
                </div>
                <p className="halo-mono" style={{ fontSize: '0.7rem', marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
                  {loadData.reasoning}
                </p>
              </div>

              <div className="system-card">
                <div className="card-header">
                  <span className="halo-mono">Active Connections</span>
                  <span className="halo-mono" style={{ color: 'var(--halo-primary)', fontSize: '1.2rem' }}>
                    {loadData.active_connections}
                  </span>
                </div>
                <p className="halo-mono" style={{ fontSize: '0.7rem', marginTop: '0.5rem', color: 'var(--text-secondary)' }}>
                  Network connections
                </p>
              </div>
            </div>
          </div>
        )}

        {/* System Resources */}
        <div className="health-section halo-panel compact-spacing">
          <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            ⚡ System Resources
          </h2>
          <div className="resources-grid">
            {['cpu', 'memory', 'disk'].map(type => {
              const resource = system.resources[type];
              return (
                <div key={type} className="resource-card">
                  <div className="resource-header">
                    <span className="halo-mono" style={{ textTransform: 'uppercase' }}>{type}</span>
                    <span className={`status-badge ${resource.status}`}>
                      {getStatusIcon(resource.healthy)}
                    </span>
                  </div>
                  <div className="resource-bar">
                    <div 
                      className="resource-fill" 
                      style={{ 
                        width: `${resource.usage_percent}%`,
                        background: `linear-gradient(90deg, ${getStatusColor(resource.status)}, transparent)`
                      }}
                    ></div>
                  </div>
                  <div className="resource-stats halo-mono">
                    <span>{resource.usage_percent}%</span>
                    {resource.used_gb !== undefined && (
                      <span>{resource.used_gb} / {resource.total_gb} GB</span>
                    )}
                    {type === 'cpu' && <span>{resource.cores} Cores</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Services */}
        <div className="health-section halo-panel compact-spacing">
          <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            🔧 System Services
          </h2>
          <div className="services-list">
            {Object.entries(services).map(([name, service]) => (
              <div key={name} className="service-item">
                <span className="service-icon">{getStatusIcon(service.healthy)}</span>
                <span className="service-name halo-mono">{name}</span>
                <span className={`service-status halo-badge ${service.status}`}>
                  {service.status}
                </span>
                {service.pid && (
                  <span className="service-pid halo-mono">PID: {service.pid}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Docker Containers */}
        <div className="health-section halo-panel compact-spacing">
          <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            🐳 Docker Containers
          </h2>
          <div className="containers-list">
            {Object.entries(containers).map(([name, container]) => (
              <div key={name} className="container-item">
                <span className="container-icon">{getStatusIcon(container.healthy)}</span>
                <span className="container-name halo-mono">{name}</span>
                <span className={`container-status halo-badge ${container.status}`}>
                  {container.status}
                </span>
                {container.restart_count !== undefined && container.restart_count > 0 && (
                  <span className="container-restarts halo-mono" style={{ color: 'var(--halo-warning)' }}>
                    ⚠️ {container.restart_count} restarts
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Network Ports */}
        <div className="health-section halo-panel compact-spacing">
          <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            🌐 Network Ports
          </h2>
          <div className="ports-grid">
            {ports.filter(p => p.port !== 80 && p.port !== 443).map(port => (
              <div key={port.port} className="port-item">
                <span className="port-icon">{getStatusIcon(port.healthy)}</span>
                <div className="port-info">
                  <span className="port-number halo-mono">{port.port}</span>
                  <span className="port-name halo-mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                    {port.name}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Services */}
        <div className="health-section halo-panel compact-spacing">
          <h2 className="halo-header" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
            🤖 AI Services
          </h2>
          <div className="ai-services-list">
            {Object.entries(ai_services).map(([name, service]) => (
              <div key={name} className="ai-service-item">
                <span className="ai-icon">{getStatusIcon(service.healthy)}</span>
                <div className="ai-info">
                  <span className="ai-name halo-mono">{service.name}</span>
                  {service.models_count !== undefined && (
                    <span className="ai-models halo-mono" style={{ fontSize: '0.7rem' }}>
                      {service.models_count} models loaded
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SystemHealth;
