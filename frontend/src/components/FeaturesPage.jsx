import PageLayout from './PageLayout';
import './FeaturesPage.css';

function FeaturesPage() {
  return (
    <PageLayout>
      <div className="features-page-content">
        {/* Hero */}
        <section className="page-hero">
          <h1 className="page-title">
            Features von <span className="gradient-text">Liara</span>
          </h1>
          <p className="page-subtitle">
            Entdecke die umfangreichen Funktionen deiner persönlichen KI-Assistentin
          </p>
        </section>

        {/* Chat System */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">💬</div>
            <h2>Intelligenter Chat</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Führe natürliche Gespräche mit verschiedenen AI-Modellen. Liara nutzt die neuesten 
              Open-Source-Modelle via Ollama und bietet dir die Wahl zwischen verschiedenen 
              Sprachmodellen für unterschiedliche Anforderungen.
            </p>
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>🤖 Mehrere AI-Modelle</h3>
                <p>Llama 3.2, Qwen 2.5, und weitere - wähle das passende Modell für deine Aufgabe</p>
              </div>
              <div className="feature-detail">
                <h3>⚡ Real-time Streaming</h3>
                <p>Server-Sent Events (SSE) für flüssige, Live-Antworten ohne Verzögerung</p>
              </div>
              <div className="feature-detail">
                <h3>🌐 Web Search Integration</h3>
                <p>DuckDuckGo, Wikipedia, Wetterdaten - alles direkt im Chat verfügbar</p>
              </div>
              <div className="feature-detail">
                <h3>💾 Unbegrenzte History</h3>
                <p>Für registrierte User - alle Gespräche werden gespeichert und durchsuchbar gemacht</p>
              </div>
            </div>
          </div>
        </section>

        {/* 4D Memory */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🧠</div>
            <h2>4D Memory System</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Ein revolutionäres Gedächtnissystem, das nicht nur Fakten speichert, sondern 
              Kontext, Emotionen und Zusammenhänge versteht - inspiriert von menschlicher Kognition.
            </p>
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>📚 Episodic Memory</h3>
                <p>Chat-Verläufe mit Session-Gruppierung - Liara erinnert sich an vergangene Gespräche</p>
              </div>
              <div className="feature-detail">
                <h3>🔍 Semantic Memory</h3>
                <p>Vektorsuche mit Neo4j - finde relevante Informationen über semantische Ähnlichkeit</p>
              </div>
              <div className="feature-detail">
                <h3>⚙️ Procedural Memory</h3>
                <p>Task-Workflows und Muster-Erkennung - Liara lernt deine Gewohnheiten</p>
              </div>
              <div className="feature-detail">
                <h3>💝 Emotional Memory</h3>
                <p>Mood-Tracking über Zeit - personalisierte Antworten basierend auf deiner Stimmung</p>
              </div>
            </div>
            <div className="tech-note">
              <strong>Technologie:</strong> PostgreSQL + Neo4j Graph + Redis Cache + 768-dim Embeddings
            </div>
          </div>
        </section>

        {/* Sentiment Analysis */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🎭</div>
            <h2>Live Sentiment-Analyse</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Liara analysiert deine Stimmung in Echtzeit während du tippst und passt ihre 
              Antworten entsprechend an - für empathischere, kontextbewusste Konversationen.
            </p>
            <div className="sentiment-categories">
              <div className="sentiment-card positive">
                <span className="sentiment-emoji">😊</span>
                <h4>Very Positive</h4>
                <p>Energetisch, freudige Sprache</p>
              </div>
              <div className="sentiment-card neutral">
                <span className="sentiment-emoji">😐</span>
                <h4>Neutral</h4>
                <p>Sachlich, informativ</p>
              </div>
              <div className="sentiment-card negative">
                <span className="sentiment-emoji">😔</span>
                <h4>Negative</h4>
                <p>Empathisch, unterstützend</p>
              </div>
              <div className="sentiment-card anxious">
                <span className="sentiment-emoji">😰</span>
                <h4>Anxious</h4>
                <p>Beruhigend, strukturiert</p>
              </div>
            </div>
            <div className="tech-note">
              <strong>Features:</strong> 500+ Keywords (DE/EN) • RegEx Pattern-Matching • 
              Debounced Analysis (800ms) • Live-Badge • Mood-Empfehlungen
            </div>
          </div>
        </section>

        {/* Productivity Tools */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">📊</div>
            <h2>Produktivitäts-Tools</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Verwalte deinen Alltag mit integrierten Tools für Tasks, Events und Notizen - 
              alles mit intelligenter AI-Unterstützung.
            </p>
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>📋 Task Management</h3>
                <p>CRUD Operations mit Priority-System (Hoch/Mittel/Niedrig)</p>
                <p>Google Calendar-Style Design mit Farbcodierung</p>
                <p>Mood-Integration für stimmungsbasierte Vorschläge</p>
              </div>
              <div className="feature-detail">
                <h3>📅 Calendar</h3>
                <p>3 View-Modi: Monat / Woche / Tag</p>
                <p>Google Calendar / Outlook-Style Grid</p>
                <p>Quick-Add durch Doppelklick</p>
              </div>
              <div className="feature-detail">
                <h3>📓 Notes</h3>
                <p>Rich Text Editing mit Categories & Tags</p>
                <p>Pin/Archive Funktionalität</p>
                <p>Intelligente Suche über alle Notizen</p>
              </div>
              <div className="feature-detail">
                <h3>🎯 Intent Detection</h3>
                <p>Automatische Erkennung im Chat</p>
                <p>"Erinnere mich an..." → Task wird erstellt</p>
                <p>"Morgen habe ich ein Meeting" → Event wird erstellt</p>
              </div>
            </div>
          </div>
        </section>

        {/* Mood Tracking */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">😊</div>
            <h2>Mood Tracking</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Verfolge deine Stimmung über Zeit mit einem wissenschaftlich fundierten 7-Dimensionen-System.
            </p>
            <div className="mood-dimensions">
              <span className="mood-tag">Joy</span>
              <span className="mood-tag">Sadness</span>
              <span className="mood-tag">Anger</span>
              <span className="mood-tag">Fear</span>
              <span className="mood-tag">Surprise</span>
              <span className="mood-tag">Disgust</span>
              <span className="mood-tag">Trust</span>
            </div>
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>📈 Zeitliche Verläufe</h3>
                <p>Grafische Darstellung deiner Stimmungsentwicklung</p>
              </div>
              <div className="feature-detail">
                <h3>🎯 Confidence Scoring</h3>
                <p>Wie sicher ist die Stimmungserkennung?</p>
              </div>
              <div className="feature-detail">
                <h3>💬 Chat Integration</h3>
                <p>Liara passt Antworten an deine aktuelle Stimmung an</p>
              </div>
            </div>
          </div>
        </section>

        {/* Guest Mode */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">👥</div>
            <h2>Guest Mode</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Teste Liara ohne Registrierung - limitierter Zugang zum Chat-System.
            </p>
            <div className="comparison-table">
              <div className="comparison-header">
                <div>Feature</div>
                <div>Guest</div>
                <div>Registered</div>
              </div>
              <div className="comparison-row">
                <div>Nachrichten</div>
                <div>20 Limit</div>
                <div>✓ Unlimited</div>
              </div>
              <div className="comparison-row">
                <div>Zeichenlimit</div>
                <div>500 Zeichen</div>
                <div>✓ Unlimited</div>
              </div>
              <div className="comparison-row">
                <div>Memory/Verlauf</div>
                <div>❌</div>
                <div>✓ 4D Memory</div>
              </div>
              <div className="comparison-row">
                <div>Sentiment-Analyse</div>
                <div>❌</div>
                <div>✓ Live</div>
              </div>
              <div className="comparison-row">
                <div>Produktivitäts-Tools</div>
                <div>❌</div>
                <div>✓ Tasks, Calendar, Notes</div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta-section">
          <h2>Bereit, Liara zu nutzen?</h2>
          <p>Registriere dich jetzt und erhalte Zugriff auf alle Features!</p>
          <a href="/" className="btn btn-primary btn-large">
            Jetzt registrieren
          </a>
        </section>
      </div>
    </PageLayout>
  );
}

export default FeaturesPage;
