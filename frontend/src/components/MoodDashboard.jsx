import { useState, useEffect } from 'react';
import { moodAPI } from '../services/api';
import './MoodDashboard.css';

const MOOD_EMOJI = {
  neutral: '😌',
  energetic: '⚡',
  calm: '🌙',
  supportive: '💜',
  focused: '🎯',
  playful: '🎨',
};

const MOOD_COLORS = {
  neutral: { primary: '#9CA3AF', gradient: 'linear-gradient(135deg, #9CA3AF 0%, #6B7280 100%)' },
  energetic: { primary: '#F59E0B', gradient: 'linear-gradient(135deg, #F59E0B 0%, #DC2626 100%)' },
  calm: { primary: '#3B82F6', gradient: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)' },
  supportive: { primary: '#8B5CF6', gradient: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)' },
  focused: { primary: '#10B981', gradient: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' },
  playful: { primary: '#EC4899', gradient: 'linear-gradient(135deg, #EC4899 0%, #BE185D 100%)' },
};

const TRAIT_ICONS = {
  warm: '🔥',
  playful: '🎭',
  analytical: '🧠',
  calm: '🌊',
};

function MoodDashboard() {
  const [moodStatus, setMoodStatus] = useState(null);
  const [moodHistory, setMoodHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resetting, setResetting] = useState(false);

  const fetchMoodStatus = async () => {
    try {
      setLoading(true);
      const data = await moodAPI.getStatus();
      setMoodStatus(data);
      setError(null);
    } catch (err) {
      setError('Fehler beim Laden des Mood-Status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMoodHistory = async () => {
    try {
      const data = await moodAPI.getHistory(10);
      setMoodHistory(data.history || []);
    } catch (err) {
      console.error('Fehler beim Laden der History:', err);
    }
  };

  const handleReset = async () => {
    if (!confirm('Mood wirklich auf Neutral zurücksetzen?')) return;
    
    try {
      setResetting(true);
      await moodAPI.reset();
      await fetchMoodStatus();
      await fetchMoodHistory();
    } catch (err) {
      alert('Fehler beim Reset: ' + err.message);
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => {
    fetchMoodStatus();
    fetchMoodHistory();
    
    // Auto-refresh alle 5 Sekunden
    const interval = setInterval(() => {
      fetchMoodStatus();
      fetchMoodHistory();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading && !moodStatus) {
    return (
      <div className="mood-dashboard loading">
        <div className="loading-spinner"></div>
        <p>Lade Mood-Status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mood-dashboard error">
        <p>{error}</p>
        <button onClick={fetchMoodStatus}>Erneut versuchen</button>
      </div>
    );
  }

  const currentMood = moodStatus?.current_mood || 'neutral';
  const intensity = moodStatus?.intensity || 0;
  const confidence = moodStatus?.confidence || 0;
  const traitModifiers = moodStatus?.trait_modifiers || {};
  const moodColor = MOOD_COLORS[currentMood];

  return (
    <div className="mood-dashboard">
      {/* Header */}
      <div className="mood-header">
        <h2>🌙 Mood-System</h2>
        <div className="mood-actions">
          <button onClick={fetchMoodStatus} className="btn-refresh" title="Aktualisieren">
            🔄
          </button>
          <button 
            onClick={handleReset} 
            className="btn-reset" 
            disabled={resetting}
            title="Mood zurücksetzen"
          >
            {resetting ? '⏳' : '↺'} Reset
          </button>
        </div>
      </div>

      {/* Current Mood Card */}
      <div 
        className="mood-current-card"
        style={{ 
          background: moodColor.gradient,
          boxShadow: `0 8px 32px ${moodColor.primary}40`
        }}
      >
        <div className="mood-emoji-large">{MOOD_EMOJI[currentMood]}</div>
        <div className="mood-info">
          <h3 className="mood-name">{currentMood}</h3>
          <div className="mood-metrics">
            <div className="metric">
              <span className="metric-label">Intensität</span>
              <span className="metric-value">{Math.round(intensity * 100)}%</span>
            </div>
            <div className="metric">
              <span className="metric-label">Confidence</span>
              <span className="metric-value">{Math.round(confidence * 100)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trait Modifiers with Animation */}
      <div className="traits-section">
        <h3>Trait-Modifiers</h3>
        <div className="traits-grid">
          {Object.entries(traitModifiers).map(([trait, value]) => {
            const percentage = Math.round(value * 100);
            return (
              <div key={trait} className="trait-item">
                <div className="trait-header">
                  <span className="trait-icon">{TRAIT_ICONS[trait] || '✨'}</span>
                  <span className="trait-name">{trait}</span>
                  <span className="trait-percentage">{percentage}%</span>
                </div>
                <div className="trait-bar">
                  <div 
                    className="trait-bar-fill"
                    style={{ 
                      width: `${percentage}%`,
                      background: moodColor.gradient,
                      animation: 'fillBar 1s ease-out'
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Mood History Minigraph */}
      <div className="history-section">
        <h3>Mood-Verlauf</h3>
        {moodHistory.length > 0 ? (
          <div className="history-graph">
            {moodHistory.map((entry, index) => (
              <div 
                key={index} 
                className="history-bar"
                style={{
                  height: `${entry.intensity * 100}%`,
                  background: MOOD_COLORS[entry.mood]?.gradient || '#666',
                  opacity: 1 - (index * 0.1)
                }}
                title={`${entry.mood} - ${Math.round(entry.intensity * 100)}% (${new Date(entry.timestamp).toLocaleTimeString()})`}
              >
                <span className="history-emoji">{MOOD_EMOJI[entry.mood]}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-history">Noch keine History verfügbar</p>
        )}
      </div>

      {/* Stats Footer */}
      <div className="mood-stats">
        <div className="stat-item">
          <span className="stat-label">History-Einträge</span>
          <span className="stat-value">{moodStatus?.history_size || 0}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Letzte Interaktion</span>
          <span className="stat-value">{moodStatus?.last_interaction || 'Keine'}</span>
        </div>
      </div>
    </div>
  );
}

export default MoodDashboard;
