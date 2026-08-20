import { useState, useEffect } from 'react';
import './ServiceManagement.css';

function ServiceManagement() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  const systemServices = [
    { 
      name: 'liara', 
      displayName: 'Liara Backend',
      description: 'FastAPI Backend Server',
      icon: '🚀'
    },
    { 
      name: 'liara-frontend', 
      displayName: 'Liara Frontend',
      description: 'Vite Development Server',
      icon: '⚛️'
    },
    { 
      name: 'nginx', 
      displayName: 'Nginx',
      description: 'Web Server & Reverse Proxy',
      icon: '🌐'
    },
    { 
      name: 'postgresql', 
      displayName: 'PostgreSQL',
      description: 'Database Server',
      icon: '🗄️'
    }
  ];

  useEffect(() => {
    fetchServiceStatus();
    const interval = setInterval(fetchServiceStatus, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchServiceStatus = async () => {
    try {
      const response = await fetch('/api/admin/services/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      const data = await response.json();
      setServices(data.services || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch service status:', error);
      setLoading(false);
    }
  };

  const handleServiceAction = async (serviceName, action) => {
    const confirmMessage = {
      start: `${serviceName} starten?`,
      stop: `${serviceName} stoppen?`,
      restart: `${serviceName} neu starten?`,
      reload: `${serviceName} neu laden?`
    };

    if (!confirm(confirmMessage[action])) {
      return;
    }

    setActionLoading(`${serviceName}-${action}`);
    try {
      const response = await fetch(`/api/admin/services/${serviceName}/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`Fehler: ${error.detail || 'Aktion fehlgeschlagen'}`);
        return;
      }

      const result = await response.json();
      alert(result.message || 'Aktion erfolgreich');
      
      // Refresh status after action
      setTimeout(fetchServiceStatus, 1000);
    } catch (error) {
      console.error('Service action failed:', error);
      alert('Fehler beim Ausführen der Aktion');
    } finally {
      setActionLoading(null);
    }
  };

  const getServiceInfo = (serviceName) => {
    return systemServices.find(s => s.name === serviceName) || {
      displayName: serviceName,
      description: 'System Service',
      icon: '⚙️'
    };
  };

  if (loading) {
    return (
      <div className="service-management">
        <div className="loading-state">
          <div className="loading-dots"><span></span><span></span><span></span></div>
          <p className="halo-mono">Lade Service-Status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="service-management">
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            ⚙️ Service-Management
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Systemdienste verwalten und überwachen
          </p>
        </div>
        <button onClick={fetchServiceStatus} className="halo-button">
          🔄 Aktualisieren
        </button>
      </div>

      <div className="services-grid">
        {services.map(service => {
          const info = getServiceInfo(service.name);
          const isActive = service.active_state === 'active';
          const isRunning = service.sub_state === 'running';
          
          return (
            <div key={service.name} className="service-card halo-panel">
              <div className="service-card-header">
                <div className="service-icon">{info.icon}</div>
                <div className="service-info">
                  <h3 className="halo-header" style={{ fontSize: '1.2rem', marginBottom: '0.25rem' }}>
                    {info.displayName}
                  </h3>
                  <p className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                    {info.description}
                  </p>
                </div>
              </div>

              <div className="service-status">
                <div className="status-row">
                  <span className="status-label halo-mono">Status:</span>
                  <span className={`status-badge ${isActive ? 'active' : 'inactive'}`}>
                    {isActive ? '✅ Aktiv' : '⛔ Inaktiv'}
                  </span>
                </div>
                <div className="status-row">
                  <span className="status-label halo-mono">Zustand:</span>
                  <span className={`status-badge ${isRunning ? 'running' : 'stopped'}`}>
                    {service.sub_state}
                  </span>
                </div>
                {service.uptime && (
                  <div className="status-row">
                    <span className="status-label halo-mono">Laufzeit:</span>
                    <span className="halo-mono" style={{ fontSize: '0.85rem' }}>
                      {service.uptime}
                    </span>
                  </div>
                )}
              </div>

              <div className="service-actions">
                {!isActive ? (
                  <button
                    onClick={() => handleServiceAction(service.name, 'start')}
                    disabled={actionLoading === `${service.name}-start`}
                    className="service-btn start-btn"
                  >
                    {actionLoading === `${service.name}-start` ? '⏳' : '▶️'} Start
                  </button>
                ) : (
                  <button
                    onClick={() => handleServiceAction(service.name, 'stop')}
                    disabled={actionLoading === `${service.name}-stop`}
                    className="service-btn stop-btn"
                  >
                    {actionLoading === `${service.name}-stop` ? '⏳' : '⏹️'} Stop
                  </button>
                )}
                <button
                  onClick={() => handleServiceAction(service.name, 'restart')}
                  disabled={actionLoading === `${service.name}-restart`}
                  className="service-btn restart-btn"
                >
                  {actionLoading === `${service.name}-restart` ? '⏳' : '🔄'} Restart
                </button>
                {service.name === 'nginx' && (
                  <button
                    onClick={() => handleServiceAction(service.name, 'reload')}
                    disabled={actionLoading === `${service.name}-reload`}
                    className="service-btn reload-btn"
                  >
                    {actionLoading === `${service.name}-reload` ? '⏳' : '♻️'} Reload
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="docker-section">
        <h2 className="halo-header" style={{ fontSize: '1.5rem', marginBottom: 'var(--space-lg)' }}>
          🐳 Docker Container
        </h2>
        <div className="docker-grid">
          <div className="service-card halo-panel">
            <div className="service-card-header">
              <div className="service-icon">📊</div>
              <div className="service-info">
                <h3 className="halo-header" style={{ fontSize: '1.2rem' }}>Neo4j</h3>
                <p className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  Graph Database
                </p>
              </div>
            </div>
            <div className="service-actions">
              <button className="service-btn" onClick={() => window.location.href = '/admin/neo4j'}>
                🌐 Browser öffnen
              </button>
              <button className="service-btn" onClick={() => window.open('/neo4j/', '_blank')}>
                🚀 Neuer Tab
              </button>
            </div>
          </div>

          <div className="service-card halo-panel">
            <div className="service-card-header">
              <div className="service-icon">🔴</div>
              <div className="service-info">
                <h3 className="halo-header" style={{ fontSize: '1.2rem' }}>Redis</h3>
                <p className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  Cache & Message Broker
                </p>
              </div>
            </div>
            <div className="service-actions">
              <button className="service-btn" onClick={() => alert('Redis läuft auf Port 6379')}>
                ℹ️ Info
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ServiceManagement;
