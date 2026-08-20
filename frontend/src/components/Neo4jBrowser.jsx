import { useState, useEffect } from 'react';
import './Neo4jBrowser.css';

function Neo4jBrowser() {
  const [isLoading, setIsLoading] = useState(true);
  const [neo4jAvailable, setNeo4jAvailable] = useState(false);

  useEffect(() => {
    checkNeo4jAvailability();
  }, []);

  const checkNeo4jAvailability = async () => {
    try {
      const response = await fetch('/neo4j/');
      setNeo4jAvailable(response.ok);
    } catch (error) {
      console.error('Neo4j not reachable:', error);
      setNeo4jAvailable(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="neo4j-browser">
        <div className="loading-state">
          <div className="loading-dots"><span></span><span></span><span></span></div>
          <p className="halo-mono">Verbinde zu Neo4j...</p>
        </div>
      </div>
    );
  }

  if (!neo4jAvailable) {
    return (
      <div className="neo4j-browser">
        <div className="page-header">
          <div>
            <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
              📊 Neo4j Browser
            </h1>
            <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Graph Database Management
            </p>
          </div>
        </div>

        <div className="halo-panel" style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-lg)' }}>⚠️</div>
          <h2 className="halo-header" style={{ fontSize: '1.5rem', marginBottom: 'var(--space-md)' }}>
            Neo4j nicht erreichbar
          </h2>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', marginBottom: 'var(--space-lg)' }}>
            Stellen Sie sicher, dass der Neo4j Docker-Container läuft
          </p>
          <div style={{ textAlign: 'left', maxWidth: '600px', margin: '0 auto' }}>
            <h3 className="halo-header" style={{ fontSize: '1rem', marginBottom: 'var(--space-md)' }}>
              💡 Troubleshooting:
            </h3>
            <div className="terminal-hints" style={{ background: 'rgba(0,0,0,0.3)', padding: 'var(--space-md)', borderRadius: '6px' }}>
              <code className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)' }}>
                docker ps | grep neo4j
              </code>
              <code className="halo-mono" style={{ display: 'block', marginBottom: 'var(--space-sm)' }}>
                docker start neo4j
              </code>
              <code className="halo-mono" style={{ display: 'block' }}>
                docker logs neo4j
              </code>
            </div>
          </div>
          <button 
            onClick={checkNeo4jAvailability}
            className="halo-button"
            style={{ marginTop: 'var(--space-lg)' }}
          >
            🔄 Erneut prüfen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="neo4j-browser">
      <div className="page-header">
        <div>
          <h1 className="halo-header" style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            📊 Neo4j Browser
          </h1>
          <p className="halo-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Graph Database Management Interface
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center' }}>
          <span className="status-indicator connected">
            🟢 Verbunden
          </span>
          <button 
            onClick={() => window.open('/neo4j/', '_blank')}
            className="halo-button"
          >
            🚀 In neuem Tab öffnen
          </button>
        </div>
      </div>

      <div className="neo4j-info halo-panel" style={{ marginBottom: 'var(--space-lg)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 'var(--space-lg)' }}>
          <div>
            <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: 'var(--space-xs)' }}>
              CONNECTION
            </div>
            <div className="halo-mono" style={{ fontSize: '0.9rem', color: 'var(--halo-primary)' }}>
              bolt://localhost:7687
            </div>
          </div>
          <div>
            <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: 'var(--space-xs)' }}>
              WEB INTERFACE
            </div>
            <div className="halo-mono" style={{ fontSize: '0.9rem', color: 'var(--halo-primary)' }}>
              http://localhost:7474
            </div>
          </div>
          <div>
            <div className="halo-mono" style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: 'var(--space-xs)' }}>
              USERNAME
            </div>
            <div className="halo-mono" style={{ fontSize: '0.9rem', color: 'var(--halo-accent)' }}>
              neo4j
            </div>
          </div>
        </div>
      </div>

      <div className="neo4j-iframe-container halo-panel">
        <iframe
          src="/neo4j/"
          title="Neo4j Browser"
          className="neo4j-iframe"
          allow="fullscreen"
        />
      </div>

      <div className="neo4j-hints halo-panel" style={{ marginTop: 'var(--space-lg)' }}>
        <h3 className="halo-header" style={{ fontSize: '1rem', marginBottom: 'var(--space-md)' }}>
          🔍 Schnelle Cypher-Queries
        </h3>
        <div className="hints-grid">
          <div className="hint-item">
            <code className="halo-mono">:help</code>
            <span>Hilfe anzeigen</span>
          </div>
          <div className="hint-item">
            <code className="halo-mono">MATCH (n) RETURN n LIMIT 25</code>
            <span>Alle Nodes anzeigen</span>
          </div>
          <div className="hint-item">
            <code className="halo-mono">MATCH (n) DETACH DELETE n</code>
            <span>⚠️ Alle Nodes löschen</span>
          </div>
          <div className="hint-item">
            <code className="halo-mono">CALL db.schema.visualization()</code>
            <span>Schema visualisieren</span>
          </div>
          <div className="hint-item">
            <code className="halo-mono">MATCH (n) RETURN count(n)</code>
            <span>Node-Anzahl</span>
          </div>
          <div className="hint-item">
            <code className="halo-mono">CALL dbms.listConfig()</code>
            <span>Konfiguration anzeigen</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Neo4jBrowser;
