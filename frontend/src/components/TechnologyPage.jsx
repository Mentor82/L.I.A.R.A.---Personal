import { Link } from 'react-router-dom';
import PageLayout from './PageLayout';
import ComplianceBadges from './ComplianceBadges';
import AITransparency from './AITransparency';
import './FeaturesPage.css';

function TechnologyPage() {
  return (
    <PageLayout>
      <div className="technology-page-content">
        {/* Hero */}
        <section className="page-hero">
          <h1 className="page-title">
            Moderne <span className="gradient-text">Technologie</span>
          </h1>
          <p className="page-subtitle">
            Liara basiert auf bewährten Open-Source-Technologien für maximale Performance, 
            Sicherheit und Skalierbarkeit.
          </p>
        </section>

        {/* AI Transparency Section */}
        <section className="feature-section">
          <AITransparency />
        </section>

        {/* Compliance Badges */}
        <section className="feature-section">
          <ComplianceBadges />
        </section>

        {/* Tech Stack Overview */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🏗️</div>
            <h2>Tech Stack</h2>
          </div>
          <div className="tech-grid">
            <div className="tech-card">
              <span className="tech-card-icon">⚡</span>
              <h3>FastAPI</h3>
              <div className="tech-version">v0.109.0</div>
              <p>
                Hochperformantes Python-Web-Framework mit automatischer API-Dokumentation, 
                async Support und Pydantic-Validierung.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">⚛️</span>
              <h3>React</h3>
              <div className="tech-version">v19.2.0</div>
              <p>
                Moderne Frontend-Library für reaktive User Interfaces mit Hooks, 
                Context API und optimiertem Rendering.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🐘</span>
              <h3>PostgreSQL</h3>
              <div className="tech-version">v14+</div>
              <p>
                Robuste relationale Datenbank für strukturierte Daten wie User, Tasks, 
                Events und Chat-History.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🔵</span>
              <h3>Neo4j</h3>
              <div className="tech-version">v5.x</div>
              <p>
                Graph-Datenbank für das 4D Memory System mit Cypher Query Language 
                und Vector Search für Embeddings.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🚀</span>
              <h3>Redis</h3>
              <div className="tech-version">v7.x</div>
              <p>
                In-Memory Cache für Session-Context, Rate Limiting und 
                Performance-Optimierung mit 1h TTL.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🤖</span>
              <h3>Ollama</h3>
              <div className="tech-version">Latest</div>
              <p>
                Lokale AI-Engine für Llama, Qwen und andere LLMs plus 
                nomic-embed-text für 768-dimensionale Embeddings.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🌐</span>
              <h3>Nginx</h3>
              <div className="tech-version">v1.22+</div>
              <p>
                Reverse Proxy für HTTPS/TLS, Load Balancing und 
                statische Frontend-Auslieferung.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🔄</span>
              <h3>Vite</h3>
              <div className="tech-version">v7.2.4</div>
              <p>
                Next-Gen Frontend-Build-Tool mit Hot Module Replacement 
                und optimiertem Production-Build.
              </p>
            </div>

            <div className="tech-card">
              <span className="tech-card-icon">🦄</span>
              <h3>Gunicorn + Uvicorn</h3>
              <div className="tech-version">Latest</div>
              <p>
                Production-Grade ASGI Server mit Multi-Worker-Setup 
                (10 workers) für hohe Verfügbarkeit.
              </p>
            </div>
          </div>
        </section>

        {/* Architecture */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🏛️</div>
            <h2>System-Architektur</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Liara folgt einer modernen Microservices-inspirierten Architektur mit 
              klarer Trennung von Frontend, Backend und Datenschichten.
            </p>

            <div className="info-box">
              <h3>📐 Architektur-Übersicht</h3>
              <pre className="architecture-diagram">
{`┌─────────────────────────────────────────┐
│         Frontend (React + Vite)         │
│  • UI Components (Chat, Tasks, etc.)    │
│  • State Management (Hooks, Context)    │
│  • API Wrappers (chatAPI, taskService)  │
└────────────────┬────────────────────────┘
                 │ HTTPS (Nginx)
                 ↓
┌─────────────────────────────────────────┐
│       Backend (FastAPI + Gunicorn)      │
│  ┌─────────────────────────────────┐   │
│  │ API Layer (20+ Routers)         │   │
│  │ • /chat, /tasks, /calendar      │   │
│  │ • /sentiment, /memory, /admin   │   │
│  └──────────────┬──────────────────┘   │
│                 │                       │
│  ┌──────────────▼──────────────────┐   │
│  │ Service Layer                   │   │
│  │ • ConfigService (Singleton)     │   │
│  │ • MemoryService (4D System)     │   │
│  │ • SentimentAnalyzer             │   │
│  │ • EmbeddingService (Ollama)     │   │
│  └──────────────┬──────────────────┘   │
└─────────────────┼───────────────────────┘
                  │
        ┌─────────┼─────────┐
        ↓         ↓         ↓
   ┌─────────┬─────────┬─────────┐
   │PostgreSQL│  Neo4j  │  Redis  │
   │  Data    │  Graph  │  Cache  │
   └─────────┴─────────┴─────────┘
                  │
                  ↓
            ┌──────────┐
            │  Ollama  │
            │ AI Models│
            └──────────┘`}
              </pre>
            </div>
          </div>
        </section>

        {/* Backend Details */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">⚙️</div>
            <h2>Backend-Technologien</h2>
          </div>
          <div className="feature-content">
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>Async/Await Pattern</h3>
                <p>
                  Vollständig asynchrones Backend mit async/await für maximale 
                  Performance bei I/O-intensiven Operationen.
                </p>
              </div>

              <div className="feature-detail">
                <h3>Dependency Injection</h3>
                <p>
                  FastAPI's Dependency-System für saubere Service-Layer-Trennung 
                  und einfaches Testing.
                </p>
              </div>

              <div className="feature-detail">
                <h3>Pydantic Validation</h3>
                <p>
                  Automatische Request/Response-Validierung mit Type-Hints 
                  und Schema-Generation.
                </p>
              </div>

              <div className="feature-detail">
                <h3>SQLAlchemy ORM</h3>
                <p>
                  Modern ORM für PostgreSQL mit async Support und 
                  Alembic-Migrationen.
                </p>
              </div>

              <div className="feature-detail">
                <h3>JWT Authentication</h3>
                <p>
                  Token-basierte Auth mit Access/Refresh-Tokens, 
                  bcrypt Password-Hashing.
                </p>
              </div>

              <div className="feature-detail">
                <h3>SSE (Server-Sent Events)</h3>
                <p>
                  Real-time Streaming für Chat-Antworten ohne WebSocket-Overhead.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Frontend Details */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🎨</div>
            <h2>Frontend-Technologien</h2>
          </div>
          <div className="feature-content">
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>React Hooks</h3>
                <p>
                  Modern Functional Components mit useState, useEffect, 
                  useContext für State Management.
                </p>
              </div>

              <div className="feature-detail">
                <h3>React Router v6</h3>
                <p>
                  Deklaratives Routing mit NavLink, Routes und 
                  Navigate für SPA-Navigation.
                </p>
              </div>

              <div className="feature-detail">
                <h3>EventSource API</h3>
                <p>
                  Native Browser-API für SSE-Streaming vom Backend 
                  mit Auto-Reconnect.
                </p>
              </div>

              <div className="feature-detail">
                <h3>react-i18next</h3>
                <p>
                  Internationalisierung (i18n) für DE/EN mit 
                  dynamischem Language-Switching.
                </p>
              </div>

              <div className="feature-detail">
                <h3>react-markdown</h3>
                <p>
                  Markdown-Rendering für Chat-Nachrichten mit 
                  Syntax-Highlighting.
                </p>
              </div>

              <div className="feature-detail">
                <h3>CSS3 Animations</h3>
                <p>
                  Glassmorphism, Gradients, Keyframe-Animationen 
                  für moderne UI/UX.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Database Schema */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">💾</div>
            <h2>Datenbank-Schema</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Hybride Datenbank-Architektur: PostgreSQL für strukturierte Daten, 
              Neo4j für Graph-Beziehungen, Redis für Caching.
            </p>

            <div className="feature-grid">
              <div className="feature-detail">
                <h3>PostgreSQL Tables</h3>
                <p>
                  users, chat_messages, tasks, calendar_events, notes, moods, 
                  sentiment_history, system_config, web_search_history
                </p>
              </div>

              <div className="feature-detail">
                <h3>Neo4j Nodes</h3>
                <p>
                  Concept, Entity, Mood, Task, Event, Note mit 
                  Relationships für Semantic Search
                </p>
              </div>

              <div className="feature-detail">
                <h3>Redis Keys</h3>
                <p>
                  session:&#123;user_id&#125;, rate_limit:&#123;ip&#125;, 
                  context:&#123;session_id&#125; mit TTL-Management
                </p>
              </div>

              <div className="feature-detail">
                <h3>Vector Embeddings</h3>
                <p>
                  768-dimensionale Vektoren (nomic-embed-text) 
                  in Neo4j für Semantic Memory
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* AI Models */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🤖</div>
            <h2>AI-Modelle</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Liara nutzt verschiedene Open-Source-LLMs via Ollama für unterschiedliche Use Cases.
            </p>

            <div className="feature-grid">
              <div className="feature-detail">
                <h3>llama3.2:1b (Guest)</h3>
                <p>Kompaktes Modell für schnelle Antworten im Guest-Modus</p>
              </div>

              <div className="feature-detail">
                <h3>llama3.2:3b (Default)</h3>
                <p>Ausgewogenes Modell für allgemeine Konversationen</p>
              </div>

              <div className="feature-detail">
                <h3>qwen2.5:7b</h3>
                <p>Größeres Modell für komplexe Anfragen und Code-Generation</p>
              </div>

              <div className="feature-detail">
                <h3>nomic-embed-text</h3>
                <p>Embedding-Modell für Semantic Search (768-dim Vektoren)</p>
              </div>
            </div>

            <div className="tech-note">
              <strong>Model Selection:</strong> Automatische Model-Auswahl basierend auf User-Rolle, 
              Prompt-Komplexität und verfügbaren Ressourcen
            </div>
          </div>
        </section>

        {/* Performance */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">⚡</div>
            <h2>Performance-Optimierungen</h2>
          </div>
          <div className="feature-content">
            <div className="feature-grid">
              <div className="feature-detail">
                <h3>Redis Caching</h3>
                <p>Session-Context mit 1h TTL für schnelleren Memory-Zugriff</p>
              </div>

              <div className="feature-detail">
                <h3>Database Indexing</h3>
                <p>Optimierte Indices für user_id, created_at, Fulltext-Search</p>
              </div>

              <div className="feature-detail">
                <h3>Connection Pooling</h3>
                <p>PostgreSQL Pool (5-20 Connections) für effiziente DB-Nutzung</p>
              </div>

              <div className="feature-detail">
                <h3>Async Processing</h3>
                <p>Non-blocking I/O für alle API-Endpoints und DB-Queries</p>
              </div>

              <div className="feature-detail">
                <h3>SSE Streaming</h3>
                <p>Chunked Transfer für Live-Antworten ohne kompletten Response-Aufbau</p>
              </div>

              <div className="feature-detail">
                <h3>Frontend Code-Splitting</h3>
                <p>Lazy Loading für Components via React.lazy und Suspense</p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta-section">
          <h2>Moderne Tech, maximale Kontrolle</h2>
          <p>Starte jetzt mit Liara und erlebe die Power von Open Source!</p>
          <Link to="/" className="btn btn-primary btn-large">
            Jetzt registrieren
          </Link>
        </section>
      </div>
    </PageLayout>
  );
}

export default TechnologyPage;
