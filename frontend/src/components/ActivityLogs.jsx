import { useState, useEffect } from 'react';
import './ActivityLogs.css';

function ActivityLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/admin/logs', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('liara_token')}`
        }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getLogIcon = (level) => {
    switch (level) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      case 'success': return '✅';
      default: return '📝';
    }
  };

  const getLogColor = (level) => {
    switch (level) {
      case 'error': return 'var(--color-danger)';
      case 'warning': return 'var(--color-warning)';
      case 'info': return 'var(--color-primary)';
      case 'success': return 'var(--color-success)';
      default: return 'var(--color-text-muted)';
    }
  };

  const filteredLogs = filter === 'all' 
    ? logs 
    : logs.filter(log => log.level === filter);

  if (loading) {
    return (
      <div className="logs-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Lade Activity Logs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="logs-container">
      {/* Header */}
      <div className="logs-header">
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--color-text)' }}>
            📝 Activity Logs
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
            System-Aktivitäten und Ereignisse
          </p>
        </div>
        <button onClick={fetchLogs} className="refresh-button">
          🔄 Aktualisieren
        </button>
      </div>

      {/* Filter */}
      <div className="logs-filter">
        {['all', 'error', 'warning', 'info', 'success'].map(level => (
          <button
            key={level}
            onClick={() => setFilter(level)}
            className={`filter-button ${filter === level ? 'active' : ''}`}
          >
            {level === 'all' ? 'Alle' : level.charAt(0).toUpperCase() + level.slice(1)}
          </button>
        ))}
      </div>

      {/* Logs List */}
      <div className="logs-list">
        {filteredLogs.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize: '48px', opacity: 0.5 }}>📝</span>
            <p>Keine Logs gefunden</p>
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} className="log-item">
              <span className="log-icon">{getLogIcon(log.level)}</span>
              <div className="log-content">
                <div className="log-message" style={{ color: getLogColor(log.level) }}>
                  {log.message}
                </div>
                <div className="log-meta">
                  <span>{new Date(log.timestamp).toLocaleString('de-DE')}</span>
                  {log.user && <span>• User: {log.user}</span>}
                  {log.source && <span>• Source: {log.source}</span>}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default ActivityLogs;
