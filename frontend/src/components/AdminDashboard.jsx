import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import RecentActivities from './dashboard/RecentActivities';
import './AdminDashboard.css';

function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const authHeader = { 'Authorization': `Bearer ${localStorage.getItem('liara_token')}` };
      const [healthRes, statsRes] = await Promise.all([
        fetch('/api/admin/health/summary', { headers: authHeader }),
        fetch('/api/dashboard/stats', { headers: authHeader }),
      ]);

      const healthData = await healthRes.json();
      setHealth(healthData);

      const statsData = await statsRes.json();
      setStats(statsData);

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="loading-state">
          <div className="loading-dots">
            <span></span><span></span><span></span>
          </div>
          <p className="halo-mono">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* Page Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            📊 Admin Dashboard
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            System-Übersicht und Verwaltung
          </p>
        </div>
        <button onClick={fetchDashboardData} className="halo-button">
          🔄 Aktualisieren
        </button>
      </div>

      {/* System Health Banner */}
      {health && (
        <div className={`health-banner halo-panel ${health.status}`}>
          <div className="health-banner-content">
            <div className="health-icon">
              {health.status === 'healthy' ? '✅' : health.status === 'degraded' ? '⚠️' : '🔴'}
            </div>
            <div className="health-info">
              <div className="halo-header" style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                System Status: {health.status === 'healthy' ? 'Alle Systeme betriebsbereit' : 'Systemprobleme erkannt'}
              </div>
              <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Health Score: {health.health_percentage.toFixed(1)}%
                {health.critical_issues && health.critical_issues.length > 0 && (
                  <span style={{ color: 'var(--halo-danger)', marginLeft: '1rem' }}>
                    {health.critical_issues.length} kritische Probleme
                  </span>
                )}
              </div>
            </div>
          </div>
          <Link to="/admin/health" className="halo-button" style={{ padding: '0.5rem 1rem' }}>
            Details anzeigen →
          </Link>
        </div>
      )}

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card halo-panel">
          <div className="stat-icon">👥</div>
          <div className="stat-content">
            <div className="stat-value">{stats?.totalUsers || 0}</div>
            <div className="stat-label">Benutzer</div>
            <div className="stat-detail halo-mono">
              {stats?.activeUsers || 0} aktiv
            </div>
          </div>
          <Link to="/admin/users" className="stat-link">Verwalten →</Link>
        </div>

        <div className="stat-card halo-panel">
          <div className="stat-icon">💬</div>
          <div className="stat-content">
            <div className="stat-value">{stats?.totalChats || 0}</div>
            <div className="stat-label">Chat-Nachrichten</div>
            <div className="stat-detail halo-mono">
              {stats?.todayChats || 0} heute
            </div>
          </div>
        </div>

        <div className="stat-card halo-panel">
          <div className="stat-icon">🤖</div>
          <div className="stat-content">
            <div className="stat-value">{stats?.aiModels || 0}</div>
            <div className="stat-label">AI Modelle</div>
            <div className="stat-detail halo-mono">
              Ollama verfügbar
            </div>
          </div>
          <Link to="/admin/models" className="stat-link">Verwalten →</Link>
        </div>

        <div className="stat-card halo-panel">
          <div className="stat-icon">💾</div>
          <div className="stat-content">
            <div className="stat-value">
              {stats?.storageUsed?.toFixed(1) || 0} GB
            </div>
            <div className="stat-label">Speicher genutzt</div>
            <div className="stat-detail halo-mono">
              von {stats?.storageTotal?.toFixed(0) || 0} GB
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions-section">
        <h2 className="halo-header" style={{ fontSize: '1.3rem', marginBottom: 'var(--space-lg)' }}>
          ⚡ Schnellaktionen
        </h2>
        <div className="quick-actions-grid">
          <Link to="/admin/users" className="quick-action-card halo-panel">
            <div className="quick-action-icon">👤</div>
            <div className="quick-action-title">Neuer Benutzer</div>
            <div className="quick-action-desc halo-mono">
              Benutzer hinzufügen
            </div>
          </Link>

          <Link to="/admin/models" className="quick-action-card halo-panel">
            <div className="quick-action-icon">📥</div>
            <div className="quick-action-title">AI Model laden</div>
            <div className="quick-action-desc halo-mono">
              Ollama Model pullen
            </div>
          </Link>

          <Link to="/admin/config" className="quick-action-card halo-panel">
            <div className="quick-action-icon">⚙️</div>
            <div className="quick-action-title">Einstellungen</div>
            <div className="quick-action-desc halo-mono">
              System konfigurieren
            </div>
          </Link>

          <Link to="/admin/logs" className="quick-action-card halo-panel">
            <div className="quick-action-icon">📋</div>
            <div className="quick-action-title">System Logs</div>
            <div className="quick-action-desc halo-mono">
              Logs anzeigen
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Activity Widget */}
      <div className="recent-activity-section">
        <RecentActivities limit={10} />
      </div>
    </div>
  );
}

export default AdminDashboard;
