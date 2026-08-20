import React from 'react';
import { SENTIMENT_EMOJIS, SENTIMENT_COLORS, formatSentiment } from '../services/sentimentService';
import './SentimentIndicator.css';

/**
 * Live Sentiment Indicator - Zeigt erkannten Gemütszustand an
 */
const SentimentIndicator = ({ sentiment, showDetails = true }) => {
  if (!sentiment || sentiment.category === 'neutral') {
    return null;  // Nichts anzeigen bei neutral
  }
  
  const formatted = formatSentiment(sentiment);
  
  return (
    <div className="sentiment-indicator" style={{ borderColor: formatted.color }}>
      <div className="sentiment-icon" style={{ color: formatted.color }}>
        {formatted.emoji}
      </div>
      
      {showDetails && (
        <div className="sentiment-details">
          <div className="sentiment-category">
            {formatted.categoryText}
          </div>
          
          <div className="sentiment-metrics">
            <div className="metric">
              <span className="metric-label">Stärke:</span>
              <div className="metric-bar">
                <div 
                  className="metric-fill"
                  style={{ 
                    width: `${formatted.intensityPercent}%`,
                    backgroundColor: formatted.color
                  }}
                />
              </div>
              <span className="metric-value">{formatted.intensityPercent}%</span>
            </div>
            
            <div className="metric">
              <span className="metric-label">Sicherheit:</span>
              <div className="metric-bar">
                <div 
                  className="metric-fill"
                  style={{ 
                    width: `${formatted.confidencePercent}%`,
                    backgroundColor: '#6366f1'
                  }}
                />
              </div>
              <span className="metric-value">{formatted.confidencePercent}%</span>
            </div>
          </div>
          
          {sentiment.indicators && sentiment.indicators.length > 0 && (
            <div className="sentiment-indicators">
              <span className="indicators-label">Erkannt:</span>
              {sentiment.indicators.slice(0, 3).map((indicator, idx) => (
                <span key={idx} className="indicator-tag">
                  {indicator.replace('pattern:', '🔍 ')}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Compact Sentiment Badge - Kleine Version für Input-Feld
 */
export const SentimentBadge = ({ sentiment }) => {
  if (!sentiment || sentiment.category === 'neutral') {
    return null;
  }
  
  const formatted = formatSentiment(sentiment);
  
  return (
    <div 
      className="sentiment-badge" 
      style={{ 
        backgroundColor: `${formatted.color}22`,
        borderColor: formatted.color
      }}
      title={`${formatted.categoryText} (${formatted.intensityPercent}% Intensität)`}
    >
      <span className="badge-emoji">{formatted.emoji}</span>
      <span className="badge-text" style={{ color: formatted.color }}>
        {formatted.categoryText}
      </span>
    </div>
  );
};

/**
 * Sentiment Pulse Animation - Pulsiert bei starken Emotionen
 */
export const SentimentPulse = ({ sentiment }) => {
  if (!sentiment || sentiment.emotion_intensity < 0.6) {
    return null;
  }
  
  const formatted = formatSentiment(sentiment);
  
  return (
    <div className="sentiment-pulse">
      <div 
        className="pulse-ring"
        style={{ 
          borderColor: formatted.color,
          animationDuration: `${2 - sentiment.emotion_intensity}s`
        }}
      />
      <div className="pulse-emoji">{formatted.emoji}</div>
    </div>
  );
};

export default SentimentIndicator;
