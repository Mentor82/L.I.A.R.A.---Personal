import { Link } from 'react-router-dom';
import PageLayout from './PageLayout';
import './FeaturesPage.css';

function PrivacyPage() {
  return (
    <PageLayout>
      <div className="privacy-page-content">
        {/* Hero */}
        <section className="page-hero">
          <h1 className="page-title">
            <span className="gradient-text">Privacy-First</span> Philosophie
          </h1>
          <p className="page-subtitle">
            Deine Daten gehören dir - und bleiben bei dir. Liara ist komplett lokal, 
            ohne Cloud-Abhängigkeit und ohne Tracking.
          </p>
        </section>

        {/* Main Privacy Statement */}
        <section className="feature-section">
          <div className="feature-content">
            <div className="info-box">
              <h3>🔒 Unsere Privacy-Versprechen</h3>
              <p>
                Liara läuft zu 100% auf deinem eigenen Server. Es gibt keine Cloud-Verbindung, 
                keine Datensammlung durch Dritte, keine versteckten Tracker. Alle Daten werden 
                lokal gespeichert und nach konfigurierbaren Zeiträumen automatisch gelöscht.
              </p>
            </div>
          </div>
        </section>

        {/* Privacy Features Grid */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🛡️</div>
            <h2>Datenschutz-Features</h2>
          </div>
          <div className="privacy-grid">
            <div className="privacy-card">
              <span className="privacy-card-icon">📋</span>
              <h3>DSGVO-Konform</h3>
              <p>
                Vollständige Compliance mit der Datenschutz-Grundverordnung. Impressum, 
                Datenschutzerklärung, AGB und Cookie-Policy sind integriert und transparent.
              </p>
            </div>

            <div className="privacy-card">
              <span className="privacy-card-icon">🏠</span>
              <h3>Keine Cloud</h3>
              <p>
                Alle Daten bleiben auf deinem Server. Keine Verbindung zu externen Cloud-Diensten, 
                keine Synchronisation mit Drittanbietern. Deine Daten verlassen nie deine Infrastruktur.
              </p>
            </div>

            <div className="privacy-card">
              <span className="privacy-card-icon">🔍</span>
              <h3>Keine Tracker</h3>
              <p>
                Zero Third-Party-Tracking. Keine Google Analytics, keine Facebook Pixel, 
                keine versteckten Tracking-Skripte. Nur essentielle Cookies für die Funktionalität.
              </p>
            </div>

            <div className="privacy-card">
              <span className="privacy-card-icon">⏰</span>
              <h3>Auto-Delete</h3>
              <p>
                Konfigurierbare Retention-Policies von 7 bis 90 Tagen. Chat-Verläufe, Sentiment-Daten 
                und Mood-Tracking werden automatisch nach Ablauf gelöscht.
              </p>
            </div>

            <div className="privacy-card">
              <span className="privacy-card-icon">🗺️</span>
              <h3>Location Opt-In</h3>
              <p>
                Standortdaten nur auf ausdrückliche Zustimmung. IP-basierte Geolocation für 
                Wetterdaten, automatisches Löschen nach 30 Tagen.
              </p>
            </div>

            <div className="privacy-card">
              <span className="privacy-card-icon">🔐</span>
              <h3>Verschlüsselung</h3>
              <p>
                HTTPS/TLS für alle Verbindungen. Passwörter werden mit bcrypt gehasht. 
                JWT-Tokens für sichere Authentifizierung.
              </p>
            </div>
          </div>
        </section>

        {/* Data Storage */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">💾</div>
            <h2>Datenspeicherung</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Transparenz über alle gespeicherten Daten - du weißt genau, was wo liegt.
            </p>
            
            <ul className="privacy-features-list">
              <li>
                <strong>Chat-Verläufe:</strong> PostgreSQL, 90 Tage Retention (konfigurierbar), 
                User-isoliert, automatisches Löschen
              </li>
              <li>
                <strong>Semantic Memory:</strong> Neo4j Graph Database, Embeddings (768-dim), 
                permanente Speicherung mit User-Consent
              </li>
              <li>
                <strong>Tasks/Events/Notes:</strong> PostgreSQL, keine Auto-Delete außer bei 
                expliziter User-Aktion
              </li>
              <li>
                <strong>Mood & Sentiment:</strong> PostgreSQL, 90 Tage Retention, 
                aggregierte Statistiken anonymisiert
              </li>
              <li>
                <strong>Session Cache:</strong> Redis, 1 Stunde TTL, automatisches Ablaufen
              </li>
              <li>
                <strong>Location Data:</strong> PostgreSQL, 30 Tage Retention (opt-in), 
                nur für Wetter-Features
              </li>
            </ul>
          </div>
        </section>

        {/* Web Safety */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🌐</div>
            <h2>Web Safety</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Sicherer Umgang mit externen Web-Ressourcen und APIs.
            </p>
            
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>Content-Filtering</h3>
                <p>Automatische Filterung von unsicheren oder schädlichen Inhalten aus Web-Searches</p>
              </div>
              <div className="feature-detail">
                <h3>Risk-Scoring</h3>
                <p>Bewertung von Web-Links und externen Ressourcen vor der Anzeige</p>
              </div>
              <div className="feature-detail">
                <h3>Rate Limiting</h3>
                <p>100 Requests/Stunde für authentifizierte User, 20/Stunde für Gäste</p>
              </div>
              <div className="feature-detail">
                <h3>Privacy-First APIs</h3>
                <p>Nur Nutzung von datenschutzfreundlichen Services (DuckDuckGo, Wikipedia, Open-Meteo)</p>
              </div>
            </div>
          </div>
        </section>

        {/* User Rights */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">⚖️</div>
            <h2>Deine Rechte (DSGVO)</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Du hast volle Kontrolle über deine Daten - jederzeit.
            </p>
            
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>Auskunftsrecht</h3>
                <p>Exportiere alle deine Daten in maschinenlesbarem Format (JSON/CSV)</p>
              </div>
              <div className="feature-detail">
                <h3>Berichtigungsrecht</h3>
                <p>Bearbeite oder korrigiere alle gespeicherten Informationen über dein Profil</p>
              </div>
              <div className="feature-detail">
                <h3>Löschrecht</h3>
                <p>Lösche deinen Account und alle zugehörigen Daten mit einem Klick</p>
              </div>
              <div className="feature-detail">
                <h3>Widerspruchsrecht</h3>
                <p>Deaktiviere einzelne Features (Location, Sentiment-Analyse) nach Belieben</p>
              </div>
              <div className="feature-detail">
                <h3>Datenportabilität</h3>
                <p>Exportiere deine Daten und migriere sie zu anderen Systemen</p>
              </div>
              <div className="feature-detail">
                <h3>Einschränkung der Verarbeitung</h3>
                <p>Pausiere bestimmte Datenverarbeitungen (z.B. Memory-System) temporär</p>
              </div>
            </div>
          </div>
        </section>

        {/* Open Source */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">📖</div>
            <h2>Open Source & Transparenz</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Vollständige Transparenz durch Open-Source-Code und dokumentierte Architekturen.
            </p>
            
            <div className="info-box">
              <h3>💡 Warum Open Source?</h3>
              <p>
                Liara nutzt ausschließlich Open-Source-Technologien (FastAPI, React, PostgreSQL, 
                Neo4j, Ollama). Der gesamte Code ist einsehbar, auditierbar und modifizierbar. 
                Keine Closed-Source-Blackboxes, keine versteckten Hintertüren.
              </p>
            </div>

            <div className="tech-note">
              <strong>Alle verwendeten Open-Source-Komponenten:</strong> FastAPI (MIT), 
              React (MIT), PostgreSQL (PostgreSQL License), Neo4j (GPL-3.0), 
              Redis (BSD-3-Clause), Ollama (MIT)
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta-section">
          <h2>Bereit für Privacy-First AI?</h2>
          <p>Starte jetzt mit Liara - deine Daten bleiben sicher bei dir!</p>
          <Link to="/" className="btn btn-primary btn-large">
            Jetzt registrieren
          </Link>
        </section>
      </div>
    </PageLayout>
  );
}

export default PrivacyPage;
