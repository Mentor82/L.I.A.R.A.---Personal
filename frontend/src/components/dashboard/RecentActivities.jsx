import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './RecentActivities.css';

const RecentActivities = ({ limit = 10 }) => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchActivities = async () => {
    try {
      const token = localStorage.getItem('liara_token');
      const response = await fetch(`/api/dashboard/activities?limit=${limit}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch activities');
      }

      const data = await response.json();
      setActivities(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchActivities, 30000);
    return () => clearInterval(interval);
  }, [limit]);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Gerade eben';
    if (diffMins < 60) return `vor ${diffMins} Min`;
    if (diffHours < 24) return `vor ${diffHours} Std`;
    if (diffDays < 7) return `vor ${diffDays} Tag${diffDays > 1 ? 'en' : ''}`;
    
    return date.toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActivityColor = (type) => {
    const colorMap = {
      'login': '#3b82f6',
      'chat': '#8b5cf6',
      'api_call': '#06b6d4',
      'error': '#ef4444',
      'system': '#64748b',
      'user': '#10b981',
      'admin': '#f59e0b'
    };
    return colorMap[type] || '#94a3b8';
  };

  if (loading) {
    return (
      <div className="recent-activities-widget">
        <div className="widget-header">
          <h3>📋 Letzte Aktivitäten</h3>
        </div>
        <div className="activities-loading">Lade Aktivitäten...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recent-activities-widget">
        <div className="widget-header">
          <h3>📋 Letzte Aktivitäten</h3>
        </div>
        <div className="activities-error">❌ {error}</div>
      </div>
    );
  }

  return (
    <div className="recent-activities-widget">
      <div className="widget-header">
        <h3>📋 Letzte Aktivitäten</h3>
        <Link to="/admin/logs" className="view-all-link">
          Alle Logs →
        </Link>
      </div>

      <div className="activities-timeline">
        {activities.length === 0 ? (
          <div className="no-activities">Keine Aktivitäten vorhanden</div>
        ) : (
          activities.map((activity) => (
            <div key={activity.id} className="activity-item-compact">
              <div 
                className="activity-icon-small"
                style={{ backgroundColor: getActivityColor(activity.type) }}
              >
                {activity.icon}
              </div>
              
              <div className="activity-content-compact">
                <span className="activity-action-compact">{activity.action}</span>
                <span className="activity-timestamp-compact">
                  {formatTimestamp(activity.timestamp)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="widget-footer">
        <Link to="/admin/logs" className="view-all-btn">
          Alle Logs anzeigen →
        </Link>
      </div>
    </div>
  );
};

export default RecentActivities;
