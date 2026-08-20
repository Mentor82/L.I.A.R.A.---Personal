import './WebSearchResults.css'

/**
 * Web Search Results Display
 * 
 * Zeigt Web-Suchergebnisse mit Quellen-Links und Risk-Score
 */
function WebSearchResults({ results, type, riskScore }) {
  if (!results) return null

  const getIcon = () => {
    switch (type) {
      case 'weather': return '🌤️'
      case 'wikipedia': return '📚'
      case 'news': return '📰'
      default: return '🌐'
    }
  }

  const getTitle = () => {
    switch (type) {
      case 'weather': return 'Wetter-Informationen'
      case 'wikipedia': return 'Wikipedia'
      case 'news': return 'Aktuelle Nachrichten'
      default: return 'Web-Suche'
    }
  }

  const getRiskBadge = () => {
    if (riskScore === undefined) return null

    let className = 'risk-safe'
    let label = 'Sicher'
    
    if (riskScore > 60) {
      className = 'risk-critical'
      label = 'Kritisch'
    } else if (riskScore > 40) {
      className = 'risk-warning'
      label = 'Warnung'
    } else if (riskScore > 20) {
      className = 'risk-caution'
      label = 'Vorsicht'
    }

    return (
      <span className={`risk-badge ${className}`} title={`Risk Score: ${riskScore}`}>
        {label}
      </span>
    )
  }

  return (
    <div className="web-search-results">
      <div className="results-header">
        <div className="results-title">
          <span className="results-icon">{getIcon()}</span>
          <span className="results-label">{getTitle()}</span>
        </div>
        {getRiskBadge()}
      </div>

      <div className="results-content">
        {/* Weather Results */}
        {type === 'weather' && results.temperature !== undefined && (
          <div className="weather-display">
            <div className="weather-temp">
              <span className="temp-value">{results.temperature}°C</span>
              <span className="temp-feels">Gefühlt: {results.feels_like || results.temperature}°C</span>
            </div>
            <div className="weather-details">
              {results.humidity && <span>💧 {results.humidity}%</span>}
              {results.wind_speed && <span>💨 {results.wind_speed} km/h</span>}
              {results.condition && <span>☁️ {results.condition}</span>}
            </div>
          </div>
        )}

        {/* Wikipedia Results */}
        {type === 'wikipedia' && results.extract && (
          <div className="wiki-display">
            {results.title && <h4 className="wiki-title">{results.title}</h4>}
            <p className="wiki-extract">{results.extract}</p>
            {results.url && (
              <a 
                href={results.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="wiki-link"
              >
                📖 Artikel auf Wikipedia lesen →
              </a>
            )}
          </div>
        )}

        {/* News/General Results */}
        {(type === 'news' || type === 'general') && results.abstract && (
          <div className="news-display">
            {results.heading && <h4 className="news-heading">{results.heading}</h4>}
            <p className="news-abstract">{results.abstract}</p>
            {results.url && (
              <a 
                href={results.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="news-link"
              >
                🔗 Quelle öffnen →
              </a>
            )}
          </div>
        )}

        {/* Source Attribution */}
        {results.source && (
          <div className="results-source">
            <span className="source-label">Quelle:</span>
            <span className="source-name">{results.source}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default WebSearchResults
