import './SearchingIndicator.css'

/**
 * Animated Searching Indicator
 * 
 * Zeigt an, dass gerade eine Web-Suche läuft
 */
function SearchingIndicator({ query, type = 'general' }) {
  const getIcon = () => {
    switch (type) {
      case 'weather': return '🌤️'
      case 'wikipedia': return '📚'
      case 'news': return '📰'
      default: return '🔍'
    }
  }

  const getLabel = () => {
    switch (type) {
      case 'weather': return 'Wetter-Daten laden...'
      case 'wikipedia': return 'Wikipedia durchsuchen...'
      case 'news': return 'Nachrichten abrufen...'
      default: return 'Suche im Internet...'
    }
  }

  return (
    <div className="searching-indicator">
      <div className="searching-icon-container">
        <div className="searching-pulse"></div>
        <div className="searching-icon">{getIcon()}</div>
      </div>
      <div className="searching-text">
        <span className="searching-label">{getLabel()}</span>
        {query && <span className="searching-query">&quot;{query}&quot;</span>}
      </div>
      <div className="searching-dots">
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  )
}

export default SearchingIndicator
