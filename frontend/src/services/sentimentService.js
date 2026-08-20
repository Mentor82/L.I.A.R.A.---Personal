/**
 * Sentiment Analysis Service - Live Stimmungserkennung
 * 
 * Analysiert User-Input in Echtzeit und erkennt emotionale Zustände.
 */

const API_BASE = '/api';

/**
 * Analysiere Sentiment eines Textes
 * @param {string} text - Zu analysierender Text
 * @param {boolean} includeMoodRecommendation - Mood-Empfehlung inkludieren?
 * @returns {Promise<Object>} Sentiment-Analyse
 */
export async function analyzeSentiment(text, includeMoodRecommendation = true) {
  try {
    const token = localStorage.getItem('liara_token');
    
    const response = await fetch(`${API_BASE}/sentiment/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        text,
        include_mood_recommendation: includeMoodRecommendation
      })
    });
    
    if (!response.ok) {
      throw new Error(`Sentiment analysis failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('❌ Sentiment analysis error:', error);
    return null;
  }
}

/**
 * Batch-Analyse mehrerer Texte
 * @param {string[]} texts - Array von Texten (max 10)
 * @returns {Promise<Object>} Batch-Analyse mit Summary
 */
export async function analyzeBatch(texts) {
  try {
    const token = localStorage.getItem('liara_token');
    
    const response = await fetch(`${API_BASE}/sentiment/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ texts })
    });
    
    if (!response.ok) {
      throw new Error(`Batch analysis failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('❌ Batch analysis error:', error);
    return null;
  }
}

/**
 * Hole Sentiment-History
 * @param {number} limit - Max Anzahl Einträge (default: 10)
 * @returns {Promise<Object>} History
 */
export async function getSentimentHistory(limit = 10) {
  try {
    const token = localStorage.getItem('liara_token');
    
    const response = await fetch(`${API_BASE}/sentiment/history?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Get history failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('❌ Get history error:', error);
    return null;
  }
}

/**
 * Hole verfügbare Sentiment-Kategorien
 * @returns {Promise<Object>} Kategorien mit Beschreibungen
 */
export async function getSentimentCategories() {
  try {
    const response = await fetch(`${API_BASE}/sentiment/categories`);
    
    if (!response.ok) {
      throw new Error(`Get categories failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('❌ Get categories error:', error);
    return null;
  }
}

/**
 * Hole Mood-Empfehlung basierend auf Text
 * @param {string} text - Zu analysierender Text
 * @returns {Promise<Object>} Mood-Empfehlung mit Response-Modifier
 */
export async function getMoodRecommendation(text) {
  try {
    const token = localStorage.getItem('liara_token');
    
    const response = await fetch(`${API_BASE}/sentiment/mood-recommendation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
      throw new Error(`Mood recommendation failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('❌ Mood recommendation error:', error);
    return null;
  }
}

/**
 * Sentiment-Emoji-Mapping
 */
export const SENTIMENT_EMOJIS = {
  'very_positive': '😊',
  'positive': '🙂',
  'neutral': '😐',
  'negative': '😔',
  'very_negative': '😢',
  'anxious': '😰',
  'excited': '🤩',
  'confused': '🤔'
};

/**
 * Sentiment-Farb-Mapping
 */
export const SENTIMENT_COLORS = {
  'very_positive': '#22c55e',  // Grün
  'positive': '#84cc16',       // Hellgrün
  'neutral': '#94a3b8',        // Grau
  'negative': '#f59e0b',       // Orange
  'very_negative': '#ef4444',  // Rot
  'anxious': '#f97316',        // Orange-Rot
  'excited': '#8b5cf6',        // Lila
  'confused': '#6366f1'        // Blau
};

/**
 * Formatiere Sentiment für UI-Anzeige
 * @param {Object} sentiment - Sentiment-Objekt
 * @returns {Object} Formatiertes Sentiment
 */
export function formatSentiment(sentiment) {
  if (!sentiment) return null;
  
  return {
    emoji: SENTIMENT_EMOJIS[sentiment.category] || '😐',
    color: SENTIMENT_COLORS[sentiment.category] || '#94a3b8',
    categoryText: sentiment.category.replace('_', ' ').toUpperCase(),
    scoreText: sentiment.score > 0 ? `+${sentiment.score}` : sentiment.score.toString(),
    confidencePercent: Math.round(sentiment.confidence * 100),
    intensityPercent: Math.round(sentiment.emotion_intensity * 100)
  };
}

/**
 * Debounced Sentiment-Analyse für Echtzeit-Input
 * @param {string} text - Input-Text
 * @param {Function} callback - Callback mit Sentiment-Ergebnis
 * @param {number} delay - Debounce-Delay in ms (default: 500)
 */
let sentimentDebounceTimer = null;

export function analyzeSentimentDebounced(text, callback, delay = 500) {
  // Clear existing timer
  if (sentimentDebounceTimer) {
    clearTimeout(sentimentDebounceTimer);
  }
  
  // Set new timer
  sentimentDebounceTimer = setTimeout(async () => {
    if (text && text.trim().length >= 5) {  // Min 5 Zeichen
      const result = await analyzeSentiment(text);
      if (result && callback) {
        callback(result);
      }
    }
  }, delay);
}

export default {
  analyzeSentiment,
  analyzeBatch,
  getSentimentHistory,
  getSentimentCategories,
  getMoodRecommendation,
  analyzeSentimentDebounced,
  formatSentiment,
  SENTIMENT_EMOJIS,
  SENTIMENT_COLORS
};
