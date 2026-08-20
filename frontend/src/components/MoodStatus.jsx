import { useState, useEffect } from 'react';
import { moodAPI } from '../services/api';
import './MoodStatus.css';

const MOOD_EMOJI = {
  neutral: '😌',
  energetic: '⚡',
  calm: '🌙',
  supportive: '💜',
  focused: '🎯',
  playful: '🎨',
};

const MOOD_COLORS = {
  neutral: '#9CA3AF',
  energetic: '#F59E0B',
  calm: '#3B82F6',
  supportive: '#8B5CF6',
  focused: '#10B981',
  playful: '#EC4899',
};

function MoodStatus() {
  const [moodStatus, setMoodStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  useEffect(() => {
    fetchMoodStatus();
    
    // Auto-refresh alle 5 Sekunden
    const interval = setInterval(fetchMoodStatus, 5000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading && !moodStatus) {
    return (
      <div className="mood-status loading">
        <p>Lade Mood-Status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mood-status error">
        <p>{error}</p>
        <button onClick={fetchMoodStatus}>Erneut versuchen</button>
      </div>
    );
  }

  const currentMood = moodStatus?.current_mood || 'neutral';
  const intensity = moodStatus?.intensity || 0;
  const traitModifiers = moodStatus?.trait_modifiers || {};

  return (
    <div className="mood-status">
      <div className="mood-header">
        <h3>Aktueller Mood</h3>
        <button onClick={fetchMoodStatus} className="refresh-btn" title="Aktualisieren">
          🔄
        </button>
      </div>

      <div 
        className="mood-current"
        style={{ borderColor: MOOD_COLORS[currentMood] }}
      >
        <div className="mood-emoji">{MOOD_EMOJI[currentMood]}</div>
        <div className="mood-name">{currentMood}</div>
        <div className="mood-intensity">
          Intensität: {Math.round(intensity * 100)}%
        </div>
      </div>

      <div className="mood-traits">
        <h4>Trait-Modifiers</h4>
        <div className="traits-grid">
          {Object.entries(traitModifiers).map(([trait, value]) => (
            <div key={trait} className="trait-item">
              <div className="trait-name">{trait}</div>
              <div className="trait-bar">
                <div 
                  className="trait-bar-fill"
                  style={{ 
                    width: `${value * 100}%`,
                    background: MOOD_COLORS[currentMood]
                  }}
                />
              </div>
              <div className="trait-value">{Math.round(value * 100)}%</div>
            </div>
          ))}
        </div>
      </div>

      {moodStatus?.last_interaction && (
        <div className="mood-last-interaction">
          Letzte Interaktion: <strong>{moodStatus.last_interaction}</strong>
        </div>
      )}
    </div>
  );
}

export default MoodStatus;
