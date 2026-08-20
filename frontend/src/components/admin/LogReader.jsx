import { useState, useEffect } from 'react';
import './LogReader.css';

const LogReader = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Filter states
  const [selectedService, setSelectedService] = useState('backend');
  const [selectedLevel, setSelectedLevel] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [limit, setLimit] = useState(100);
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  const services = ['backend', 'sse', 'frontend'];
  const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('liara_token');
      const params = new URLSearchParams({
        service: selectedService,
        limit: limit.toString()
      });
      
      if (selectedLevel) params.append('level', selectedLevel);
      if (searchTerm) params.append('search', searchTerm);
      
      const response = await fetch(`/api/admin/logs?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [selectedService, selectedLevel, limit]);

  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedService, selectedLevel, limit, searchTerm]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchLogs();
  };

  const getLevelClass = (level) => {
    const levelMap = {
      'DEBUG': 'debug',
      'INFO': 'info',
      'WARNING': 'warning',
      'ERROR': 'error',
      'CRITICAL': 'critical'
    };
    return levelMap[level] || 'info';
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className="log-reader">
      <div className="log-reader-header">
        <h2>📋 System Logs</h2>
        <div className="header-actions">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span>Auto-Refresh (5s)</span>
          </label>
          <button onClick={fetchLogs} disabled={loading} className="refresh-btn">
            🔄 Aktualisieren
          </button>
        </div>
      </div>

      <div className="log-filters">
        <div className="filter-group">
          <label>Service:</label>
          <div className="service-tabs">
            {services.map(service => (
              <button
                key={service}
                className={`service-tab ${selectedService === service ? 'active' : ''}`}
                onClick={() => setSelectedService(service)}
              >
                {service.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <label>Log Level:</label>
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="level-select"
          >
            <option value="">Alle Levels</option>
            {levels.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Limit:</label>
          <select
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value))}
            className="limit-select"
          >
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
            <option value="500">500</option>
          </select>
        </div>

        <form onSubmit={handleSearch} className="filter-group search-group">
          <label>Suche:</label>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Suche in Logs..."
            className="search-input"
          />
          <button type="submit" className="search-btn">🔍</button>
        </form>
      </div>

      {error && (
        <div className="log-error">
          ❌ {error}
        </div>
      )}

      <div className="log-container">
        {loading && logs.length === 0 ? (
          <div className="loading">Lade Logs...</div>
        ) : (
          <div className="log-entries">
            {logs.map((log, index) => (
              <div key={index} className={`log-entry level-${getLevelClass(log.level)}`}>
                <div className="log-timestamp">{formatTimestamp(log.timestamp)}</div>
                <div className="log-level">{log.level}</div>
                <div className="log-message">{log.message}</div>
              </div>
            ))}
            {logs.length === 0 && (
              <div className="no-logs">Keine Logs gefunden</div>
            )}
          </div>
        )}
      </div>

      <div className="log-footer">
        <span className="log-count">{logs.length} Einträge</span>
        {autoRefresh && <span className="refresh-indicator">🔄 Auto-Refresh aktiv</span>}
      </div>
    </div>
  );
};

export default LogReader;
