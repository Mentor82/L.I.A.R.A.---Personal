import PageLayout from './PageLayout';
import ArchitectureMap from './ArchitectureMap';
import './FeaturesPage.css';

function ArchitecturePage() {
  return (
    <PageLayout>
      <div className="architecture-page-content">
        <section className="page-hero" style={{ paddingBottom: '1.5rem' }}>
          <h1 className="page-title">
            <span className="gradient-text">Architektur</span>-Übersicht
          </h1>
        </section>

        <section className="feature-section">
          <ArchitectureMap />
        </section>

        <p className="page-subtitle" style={{ maxWidth: 'none', marginTop: '1.5rem' }}>
          Eine interaktive Karte der LIARA-Personal-Komponenten: was zusammenhängt,
          was lokal bleibt, was implementiert ist - und wo die Grenze zu Ollama Cloud
          liegt. Komponente anklicken für Details.
        </p>

        <div className="privacy-note" style={{ marginTop: '1rem' }}>
          <p>
            ℹ️ <strong>Stand:</strong> 23. August 2026. Diese Karte beschreibt den zu diesem
            Zeitpunkt tatsächlich implementierten Stand - bei größeren Architektur-Änderungen
            sollte sie mit aktualisiert werden.
          </p>
        </div>
      </div>
    </PageLayout>
  );
}

export default ArchitecturePage;
