import PageLayout from './PageLayout';
import MermaidDiagram from './MermaidDiagram';
import './FeaturesPage.css';

const SYSTEM_CONTEXT = `flowchart TD
    User["👤 Nutzer / Browser"]
    FE["React Frontend<br/>Vite SPA"]
    BE["Liara Backend<br/>FastAPI"]
    Ollama["Ollama Runtime<br/>lokale + Cloud-Modelle"]
    SearXNG["SearXNG<br/>self-hosted, nur localhost"]
    Web["Externe Webseiten<br/>via sicherem Server-Fetch"]
    RPi5["RPi5 + Hailo-8L NPU<br/>optionaler Vision-Beschleuniger"]

    User -->|HTTPS| FE
    FE -->|REST + SSE| BE
    BE -->|Prompts, native Tool-Calls| Ollama
    BE -->|Recherche-Anfragen| SearXNG
    BE -.->|sicherer Abruf einzelner Quellen| Web
    BE -.->|optionale Vision-Tasks| RPi5`;

const CONTAINER_VIEW = `flowchart TD
    subgraph FE["Frontend"]
        React["React SPA"]
    end
    subgraph BE["Liara Backend"]
        Gunicorn["liara-backend.service<br/>Gunicorn, 6 Worker, :8100"]
        SSE["liara-sse.service<br/>Uvicorn, 3 Worker, :8101"]
    end
    subgraph Daten["Datenhaltung"]
        PG[("PostgreSQL<br/>+ pgvector")]
        Neo[("Neo4j<br/>Concept-Graph")]
        Redis[("Redis<br/>Rate-Limit, Cache, Sessions")]
    end
    subgraph Extern["Externe Dienste (Docker, localhost)"]
        OllamaS["Ollama"]
        SearXNGS["SearXNG<br/>127.0.0.1:8080"]
    end

    React -->|"/api/*"| Gunicorn
    React -->|"/api/chat/stream"| SSE
    Gunicorn --> PG
    Gunicorn --> Neo
    Gunicorn --> Redis
    SSE --> PG
    SSE --> Neo
    SSE --> Redis
    Gunicorn --> OllamaS
    SSE --> OllamaS
    SSE --> SearXNGS`;

const CHAT_FLOW = `flowchart TD
    Msg["User-Nachricht"] --> Mem["Memory-Kontext<br/>Neo4j + pgvector"]
    Mem --> Prompt["System-Prompt<br/>+ Konversationsverlauf"]
    Prompt --> Ollama["Ollama, Streaming"]
    Ollama -->|"natives thinking-Feld"| E1["SSE: thinking"]
    Ollama -->|"&lt;tasks&gt;-Block"| E2["SSE: tasks<br/>modellbehauptet"]
    Ollama -->|"tool_calls"| Agent["Agent-Loop<br/>bis zu 3 Zusatzrunden"]
    Agent -->|"Tool-Status"| E3["SSE: agent_steps<br/>system-bestätigt"]
    Agent -->|"web_search-Quellen"| E4["SSE: web_sources"]
    Ollama -->|"Antworttext"| E5["SSE: content"]
    E5 --> Persist["Persistenz<br/>chat_messages"]
    Persist -->|"DB-Commit bestätigt"| E6["SSE: persisted"]`;

const AGENT_TOOL_FLOW = `flowchart TD
    Model["Ollama-Modell<br/>(tool-fähig, siehe /api/show)"] -->|"tool_calls"| Registry["tool_registry.py"]
    Registry --> Executor["tool_executor.py"]
    Executor --> Consent{"Consent-Check<br/>allow_web_search /<br/>Standort-Consent"}
    Consent -->|erlaubt| Tools

    subgraph Tools["Verfügbare Tools"]
        WS["web_search<br/>instant / web / wikipedia"]
        Time["get_current_time"]
        Weather["get_weather"]
        Loc["detect_location"]
    end

    WS -->|"search_type=web"| Broker["SearchBroker"]
    Broker --> SearXNG["SearXNG"]
    Broker --> Sandbox["ProxySandbox<br/>SSRF-gehärtet"]
    Sandbox --> Evidence["Evidence-Records<br/>Titel, Domain, Text, Datum"]
    Evidence --> Model

    Code["Code-Run-Button<br/>(Python/Julia)"] --> Runner["run_sandboxed.sh<br/>liara-runner OS-User"]
    Runner --> Isolated["unshare --net<br/>netzwerk-isoliert"]`;

const MEMORY_FLOW = `flowchart TD
    Chat["Chat-Nachricht"] --> PG[("PostgreSQL<br/>chat_messages")]
    Chat --> Concepts["spaCy POS-Extraktion<br/>(NOUN/PROPN)"]
    Concepts --> Neo[("Neo4j<br/>Concept-Graph")]
    ToolCall["Agent-Tool-Aufruf"] --> RedisCache[("Redis<br/>Search-Cache, 10 Min TTL")]
    WebSafety["Web-Safety-Layer"] --> RedisRL[("Redis<br/>Sliding-Window Rate-Limit")]
    CodeRun["Code-Ausführung"] --> Workspace["Session-Workspace<br/>Dateien pro Session"]`;

const INFRA_VIEW = `flowchart TD
    Client["Internet / LAN"] --> Nginx["nginx<br/>TLS-Terminierung"]
    Nginx -->|"/api/chat/stream"| SSEProc["liara-sse.service<br/>Uvicorn :8101"]
    Nginx -->|"/api/*"| Backend["liara-backend.service<br/>Gunicorn :8100"]
    Nginx -->|"/"| Static["Frontend Static Build"]
    Backend --> Docker
    SSEProc --> Docker
    subgraph Docker["Docker-Container"]
        RedisC["Redis"]
        Neo4jC["Neo4j"]
        SearXNGC["SearXNG<br/>127.0.0.1:8080 - nie öffentlich"]
    end
    Backend --> OllamaSvc["Ollama-Service"]
    SSEProc --> OllamaSvc`;

function ArchitecturePage() {
  return (
    <PageLayout>
      <div className="architecture-page-content">
        {/* Hero */}
        <section className="page-hero">
          <h1 className="page-title">
            <span className="gradient-text">Architektur</span>-Übersicht
          </h1>
          <p className="page-subtitle">
            Wie Liara aufgebaut ist - vom Nutzer-Request bis zur Antwort.
            Diese Seite beschreibt den tatsächlich implementierten Stand, nicht
            geplante Features - sie kann trotzdem veralten, wenn sich die
            Architektur ändert und diese Seite nicht mitgepflegt wird.
          </p>
        </section>

        {/* 1. System Context */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🌐</div>
            <h2>1. System-Kontext</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Liara läuft als Web-App mit eigenem Backend. Sprachmodelle laufen über Ollama
              (lokal oder als Cloud-Modell), Recherche läuft über ein selbstgehostetes,
              keyless SearXNG - niemals über kommerzielle Such-APIs.
            </p>
            <div className="info-box">
              <MermaidDiagram code={SYSTEM_CONTEXT} />
            </div>
          </div>
        </section>

        {/* 2. Container/Service View */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🏗️</div>
            <h2>2. Container- / Service-View</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Das Backend läuft als zwei getrennte Prozesse mit identischer Codebasis:
              Gunicorn für normale API-Requests, ein separater Uvicorn-Prozess ausschließlich
              für den Chat-Stream (Server-Sent Events dürfen nicht hinter Gunicorns Worker-Queue
              warten). Redis, Neo4j und SearXNG laufen als Docker-Container auf demselben Host.
            </p>
            <div className="info-box">
              <MermaidDiagram code={CONTAINER_VIEW} />
            </div>
          </div>
        </section>

        {/* 3. Primary Chat Data Flow */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">💬</div>
            <h2>3. Chat-Datenfluss</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Eine Antwort besteht aus mehreren separaten SSE-Ereignistypen, nicht nur reinem
              Text - Denkprozess, ein vom Modell selbst behauptetes Aufgaben-Update und
              system-bestätigte Agent-Schritte sind bewusst getrennte Kanäle, damit die Oberfläche
              nie verwechselt, was das Modell nur behauptet und was tatsächlich ausgeführt wurde.
            </p>
            <div className="info-box">
              <MermaidDiagram code={CHAT_FLOW} />
            </div>
          </div>
        </section>

        {/* 4. Agent / Tool / Code-Execution Flow */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">⚙️</div>
            <h2>4. Agent-, Tool- und Code-Ausführungs-Flow</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Tool-fähige Modelle (geprüft über Ollamas <code>/api/show</code>) können bis zu
              drei zusätzliche Runden lang selbst Tools aufrufen, bevor eine finale Antwort
              erzwungen wird. Jeder Tool-Aufruf durchläuft zuerst einen echten Consent-Check
              (abschaltbar in den Privacy-Einstellungen). Recherche-Anfragen laufen über SearXNG
              und werden mit echten, SSRF-geschützt abgerufenen Quellentexten angereichert.
              Code-Ausführung (Run-Button) ist komplett getrennt: eigener OS-User, eigener
              Netzwerk-Namespace.
            </p>
            <div className="info-box">
              <MermaidDiagram code={AGENT_TOOL_FLOW} />
            </div>
          </div>
        </section>

        {/* 5. Persistence & Memory Flow */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🗄️</div>
            <h2>5. Persistenz- und Memory-Flow</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              Konversationen landen dauerhaft in PostgreSQL. Für das Langzeit-Gedächtnis werden
              Konzepte (Nomen/Eigennamen, per spaCy extrahiert) als Graph in Neo4j gespeichert.
              Redis übernimmt ausschließlich kurzlebige Daten - Rate-Limiting und einen kurzen
              Suchergebnis-Cache -, nie die eigentliche Konversation.
            </p>
            <div className="info-box">
              <MermaidDiagram code={MEMORY_FLOW} />
            </div>
          </div>
        </section>

        {/* 6. Infrastructure / Deployment View */}
        <section className="feature-section">
          <div className="feature-header">
            <div className="feature-icon-large">🔌</div>
            <h2>6. Infrastruktur- / Deployment-View</h2>
          </div>
          <div className="feature-content">
            <p className="feature-description">
              nginx terminiert TLS und verteilt Requests: der Chat-Stream-Endpunkt geht direkt
              an den separaten SSE-Prozess, alles andere an Gunicorn. SearXNG ist bewusst nur
              auf <code>127.0.0.1</code> gebunden - nie öffentlich oder im LAN erreichbar,
              ausschließlich vom Backend-Prozess selbst aufrufbar.
            </p>
            <div className="info-box">
              <MermaidDiagram code={INFRA_VIEW} />
            </div>
          </div>
        </section>

        <div className="privacy-note" style={{ marginTop: '1rem' }}>
          <p>
            ℹ️ <strong>Stand:</strong> 23. August 2026. Diese Seite beschreibt den zu diesem
            Zeitpunkt tatsächlich implementierten Stand - bei größeren Architektur-Änderungen
            sollte sie mit aktualisiert werden, sonst veraltet sie wie die vorherige, rein
            textuelle Dokumentation es tat.
          </p>
        </div>
      </div>
    </PageLayout>
  );
}

export default ArchitecturePage;
