# 🌙 LIARA - Feature-Übersicht

**Version:** 2.0 (Stand: 3. Dezember 2025)  
**Architektur:** Full-Stack AI Assistant (FastAPI + React + Vite)  
**Design:** Halo/UNSC-inspiriert (Cortana Theme)

---

## 🎯 Kernfunktionen

### 1. 💬 Chat-System (Dual-Mode)

#### Authentifizierter Modus
- **Multi-Model Support:**
  - llama3.2:3b (Standard, balanced)
  - llama3.2:1b (schnell, ressourcenschonend)
  - qwen2.5:7b (erweitert, leistungsstark)
  - Dynamische Modellauswahl per UI
- **Memory System:**
  - 4D-Speicher: Episodic, Semantic, Procedural, Emotional
  - PostgreSQL + Neo4j Graph-DB für Kontext
  - Redis Cache für Session-Persistenz
  - Automatische Kontext-Injektion (letzte 5-10 Nachrichten)
- **Streaming:**
  - Server-Sent Events (SSE) für Echtzeit-Antworten
  - Progressive Anzeige während KI-Generierung
  - Web-Search-Integration mit Live-Status
- **Advanced Features:**
  - Unbegrenzte Nachrichtenlänge
  - Vollständiger Verlauf
  - Stimmungserkennung (Mood Detection)
  - Kontextbasierte Antworten

#### Gast-Modus (Ohne Registrierung)
- **Modell:** llama3.2:1b (optimiert für Geschwindigkeit)
- **Limits:**
  - 20 Nachrichten pro Session
  - 500 Zeichen pro Nachricht
  - Kein Speicher/Verlauf
- **Web-Search Support:**
  - Wetter (Open-Meteo API)
  - Wikipedia (MediaWiki API)
  - News (DuckDuckGo)
  - Allgemeine Websuche
- **Streaming:** SSE mit Web-Search-Live-Anzeige

---

### 2. 🧠 Memory System (4D-Architektur)

#### Episodic Memory (Ereignisse)
- Chat-Nachrichten mit Timestamps
- Session-basierte Gruppierung
- Automatische Retention: 90 Tage
- PostgreSQL Storage

#### Semantic Memory (Wissen)
- Embeddings via Ollama (nomic-embed-text)
- Vektorsuche für semantische Ähnlichkeit
- Kontext-Extraktion aus Konversationen
- Neo4j Graph-Relationships

#### Procedural Memory (Abläufe)
- Task-Workflows
- Wiederkehrende Muster
- Automatisierte Prozesse

#### Emotional Memory (Stimmungen)
- Mood-Tracking über Zeit
- Sentiment-Analyse
- Stimmungsbasierte Antwortanpassung

**Technische Details:**
- **Embedding-Dimensionen:** 768 (nomic-embed-text)
- **Graph-DB:** Neo4j (Beziehungen zwischen Konzepten)
- **Cache-Layer:** Redis (Session-Context, 1h TTL)
- **Auto-Cleanup:** Cron-Jobs für Datenbereinigung

---

### 3. 🌐 Web-Integration & Privacy

#### External Search Service
- **DuckDuckGo API:** Privacy-First Suchmaschine
- **Wikipedia API:** Wissensdatenbank (MediaWiki)
- **Open-Meteo API:** Wetterdaten (FOSS, kein API-Key)
- **IP-API:** Geolocation (opt-in, 30 Tage Retention)

#### Web Safety System
- **URL Risk Analysis:**
  - Malicious Domain Detection
  - Phishing-Schutz
  - Content-Type Validation
- **Rate Limiting:**
  - 100 Requests/Stunde (authenticated)
  - 20 Requests/Stunde (guest)
- **Content Fetching:**
  - HTML to Text Extraktion
  - Metadata Parsing
  - Timeout: 10 Sekunden
- **Logging & Stats:**
  - Request-Historie (Admin)
  - Risk-Level-Tracking
  - Performance-Metriken

#### Privacy Features
- **Location Services:**
  - Opt-in Geolocation
  - Manuelle Freigabe pro Request
  - Auto-Delete nach 30 Tagen
  - Koordinaten-Anonymisierung (2 Dezimalstellen)
- **Web-Search Privacy:**
  - DuckDuckGo (No Tracking)
  - Auto-Delete Suchhistorie (7 Tage)
  - Keine IP-Logs
- **Data Export:**
  - DSGVO-konform: JSON-Export aller Nutzerdaten
  - On-Demand Download
- **Data Deletion:**
  - Vollständige Datenlöschung (alle Services)
  - PostgreSQL, Neo4j, Redis, Logs

---

### 4. 🌙 Mood-Tracking

- **Stimmungserkennung:**
  - Automatische Analyse aus Chat-Inhalten
  - NLP-basierte Sentiment-Detection
  - 7 Basis-Stimmungen: Neutral, Happy, Sad, Angry, Anxious, Excited, Calm
- **Modifiers:**
  - Energielevel (1-10)
  - Stress-Level (1-10)
  - Produktivität (1-10)
- **Dashboard:**
  - Tages-/Wochen-/Monatsansicht
  - Stimmungsverlauf (Diagramme)
  - Korrelationen & Muster
- **Integration:**
  - Antwortanpassung basierend auf Stimmung
  - Mood-Context in Memory-System

---

### 5. ✅ Task-Management

- **Features:**
  - Task-Erstellung mit Priorität (Low/Medium/High)
  - Kategorien & Tags
  - Deadlines & Reminders
  - Subtasks (verschachtelt)
- **Smart Views:**
  - Tägliche Agenda
  - Wochenplanung
  - Überfällige Tasks
  - Kategoriefilter
- **AI-Integration:**
  - Task-Extraktion aus Chat
  - Automatische Priorisierung
  - Deadline-Vorschläge

---

### 6. 📅 Kalender

- **Event-Management:**
  - Termine mit Start/End-Zeit
  - Ganztägige Events
  - Wiederholende Events
  - Kategorien & Farben
- **Konflikt-Erkennung:**
  - Überschneidungs-Check
  - Freie Zeitslots finden
- **Views:**
  - Tagesansicht
  - Wochenansicht
  - Monatsansicht
  - Agenda-Liste

---

### 7. 📓 Notizen-System

- **Features:**
  - Markdown-Support
  - Rich-Text-Editor
  - Code-Syntax-Highlighting
  - Kategorien & Tags
- **Organisation:**
  - Pin wichtige Notizen
  - Archivierung
  - Volltext-Suche
  - Tag-basierte Filter
- **AI-Features:**
  - Automatische Zusammenfassungen
  - Tag-Vorschläge
  - Verknüpfung mit Chat-Context

---

### 8. 🔐 Authentifizierung & User-Management

#### Auth-System
- **JWT-basiert:**
  - Access Token (24h Gültigkeit)
  - Refresh Token (7 Tage)
  - Secure HTTP-Only Cookies
- **Features:**
  - Registrierung mit Email-Validierung
  - Login/Logout
  - Token-Refresh
  - Session-Management

#### User-Rollen
- **Admin:**
  - Vollzugriff auf alle Features
  - User-Management
  - System-Monitoring
  - Datenbankzugriff
- **User:**
  - Standard-Features
  - Eigene Daten
  - Keine Admin-Funktionen
- **Guest:**
  - Eingeschränkter Chat
  - Keine Persistenz
  - Web-Search erlaubt

#### User-Management (Admin)
- User aktivieren/deaktivieren
- Rollen ändern
- User löschen
- Aktivitäts-Logs

---

### 9. 🏥 System Health Monitoring (Admin)

#### Resource Monitoring
- **CPU:**
  - Auslastung in %
  - Anzahl Cores
  - Status: Healthy (<70%), Warning (70-90%), Critical (>90%)
- **Memory:**
  - Total/Used/Available (GB)
  - Nutzung in %
  - 3-stufige Schwellwerte
- **Disk:**
  - Total/Used/Free (GB)
  - Nutzung in %
  - Speicherplatz-Alerts

#### Service Monitoring
- **Systemd Services:**
  - liara-backend (FastAPI)
  - liara-frontend (Vite)
  - nginx (Reverse Proxy)
  - postgresql (Datenbank)
  - docker (Container Runtime)
- **Live-Status:**
  - Running/Stopped/Failed
  - PID-Tracking
  - Restart-Counter

#### Network Monitoring
- **Ports:**
  - 8100 (FastAPI Backend)
  - 5173 (Vite Frontend)
  - 80/443 (Nginx HTTP/HTTPS)
  - 5432 (PostgreSQL)
  - 6379 (Redis)
  - 7474/7687 (Neo4j HTTP/Bolt)
  - 11434 (Ollama API)
- **Status:** Listening/Closed

#### Container Health
- **Docker Containers:**
  - liara-redis
  - liara-neo4j
- **Checks:**
  - Running State
  - Restart Count
  - Uptime
  - Resource Usage

#### Database Health
- **PostgreSQL:**
  - Connection Test
  - Version Info
  - Table Count
  - Query Performance

#### AI Service Health
- **Ollama:**
  - Verfügbarkeit
  - Geladene Modelle
  - Model Count

#### Health Dashboard
- **Overall Score:** 0-100% (Passed Checks / Total Checks)
- **Status Levels:**
  - Healthy: ≥80%
  - Degraded: 50-80%
  - Critical: <50%
- **Alerts:**
  - Critical Issues List
  - Resource Warnings
  - Service Failures
- **Auto-Refresh:** 30 Sekunden
- **Endpoints:**
  - `/admin/health/full` - Vollständige Diagnostik
  - `/admin/health/summary` - Kompakte Dashboard-Ansicht

---

### 10. ⚙️ Ollama-Integration

- **Model Management:**
  - Verfügbare Modelle auflisten
  - Modelle pullen (Download)
  - Pull-Status-Tracking
  - Model-Details anzeigen
- **Library Search:**
  - Ollama Model Hub durchsuchen
  - Filter nach Größe/Typ
  - Empfehlungen basierend auf GPU
- **Storage Management:**
  - Speicherplatz-Übersicht
  - Model-Größen
  - Cleanup-Tools

---

### 11. 🎮 GPU-Support

- **GPU-Detection:**
  - NVIDIA CUDA Check
  - AMD ROCm Support
  - Intel oneAPI Detection
- **Recommendations:**
  - Model-Empfehlungen basierend auf VRAM
  - Performance-Optimierungen
  - Ressourcen-Warnings
- **Status-Dashboard:**
  - GPU-Typ & Treiber
  - VRAM-Nutzung
  - CUDA-Version

---

### 12. 🎨 Halo/UNSC Design System

#### Farbpalette
- **Primary:** #00D9FF (Cortana Cyan)
- **Secondary:** #0A84FF (UNSC Blue)
- **Accent:** #00FFB3 (Energy Shield Green)
- **Warning:** #FFD60A (Caution Yellow)
- **Danger:** #FF453A (Critical Red)

#### Visuelle Effekte
- **Hintergrund:**
  - Hexagon-Grid-Pattern (60°/120° repeating gradients)
  - Animated Scan-Line (horizontal sweep)
  - Deep Space Farben (#0A0E1A)
- **Panels:**
  - Gradient-Borders (Cortana Glow)
  - Box-Shadows mit Neon-Effekten
  - Glass-Morphism (backdrop-filter)
- **Buttons:**
  - Hover-Glow-Effekte
  - ::before Pseudo-Element Animationen
  - Cortana-Cyan-Highlight

#### Typografie
- **Primary:** Rajdhani, Orbitron, Roboto Mono
- **Mono:** Fira Code, JetBrains Mono
- **HUD-Style:** Uppercase, Letter-Spacing, Monospace

#### Komponenten
- `.halo-panel` - Container mit Glow-Border
- `.halo-button` - Interactive Buttons
- `.halo-badge` - Status-Badges
- `.halo-header` - Section Headers
- `.halo-divider` - Section Separators
- `.halo-mono` - Monospace Text

#### Spacing-System (Kompakt)
- `--space-xs`: 0.25rem
- `--space-sm`: 0.5rem
- `--space-md`: 0.75rem
- `--space-lg`: 1rem
- `--space-xl`: 1.5rem
- `--space-2xl`: 2rem

---

### 13. 📱 Mobile Navigation

- **Hamburger Menu:**
  - 3-Line Animation
  - Slide-in von rechts (85% width, max 320px)
  - Overlay mit Blur-Effekt
- **Menu-Struktur:**
  - User-Avatar & Info (oben)
  - Navigation-Sektion (Hauptfunktionen)
  - Legal-Sektion (Rechtliches)
  - Logout-Button (unten)
- **Features:**
  - Touch-optimiert
  - Swipe-to-Close (geplant)
  - Context-aware (Guest vs. User)
  - Admin-Links (role-based)
- **Responsive:**
  - Anzeige nur bei <768px
  - Desktop: Standard-Navigation

---

### 14. 📜 Rechtliche Seiten (DSGVO-konform)

#### Impressum
- TMG §5 konform
- Angaben gemäß Telemediengesetz
- Kontaktdaten
- Verantwortlicher
- Haftungsausschluss (Inhalte, Links, Urheberrecht)

#### Datenschutzerklärung
- **Privacy by Design erklärt:**
  - Lokale KI (100% on-premise)
  - Keine Cloud-Services
  - Open-Source-Transparenz
- **Datenarten:**
  - Username, Email (verschlüsselt)
  - Chat-Nachrichten (lokale DB)
  - Location (opt-in, 30 Tage)
  - Web-Searches (7 Tage Retention)
- **Externe Services:**
  - DuckDuckGo (No Tracking)
  - Wikipedia (No Tracking)
  - Open-Meteo (FOSS, kein API-Key)
  - ip-api.com (Geolocation, opt-in)
- **Rechte:**
  - Auskunft
  - Berichtigung
  - Löschung
  - Datenportabilität (JSON-Export)
- **Badge:** "PRIVACY FIRST • NO CLOUD • NO TRACKING"

#### AGB
- Leistungsumfang (Self-Hosted AI Assistant)
- Nutzungsbedingungen
- Haftungsausschluss
- Open-Source-Lizenz-Hinweis
- Änderungsvorbehalt

#### Cookie-Richtlinie
- **Essential Only:**
  - `liara_token` (JWT, 24h)
  - `liara_guest_mode` (Boolean)
- **Kein Tracking:**
  - Keine Google Analytics
  - Kein Facebook Pixel
  - Keine Werbe-Cookies
- **LocalStorage:**
  - User-Daten (JSON)
  - Session-State
- **Badge:** "NO TRACKING • ESSENTIAL ONLY • PRIVACY"

---

## 🛠️ Technischer Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Sprache:** Python 3.11+
- **Datenbanken:**
  - PostgreSQL 15+ (Relational, Hauptdatenbank)
  - Neo4j 5.x (Graph-DB für Memory-Relationships)
  - Redis 7.x (Cache & Session-Store)
- **AI/ML:**
  - Ollama (LLM-Host)
  - nomic-embed-text (Embeddings)
  - llama3.2:1b/3b, qwen2.5:7b (Models)
- **ORM:** SQLAlchemy 2.x
- **Auth:** JWT (python-jose)
- **Async:** httpx, asyncio
- **System:** psutil, platform

### Frontend
- **Framework:** React 19.2.0
- **Build-Tool:** Vite 7.2.4
- **Routing:** React Router DOM
- **Styling:** Pure CSS (Halo Theme)
- **HTTP:** Fetch API, EventSource (SSE)
- **State:** React Hooks (useState, useEffect, useContext)

### Infrastructure
- **Web-Server:** Nginx (Reverse Proxy)
- **Process-Manager:** Systemd
  - liara-backend.service
  - liara-frontend.service
- **Containerization:** Docker (Redis, Neo4j)
- **OS:** Linux (Debian-based)

### APIs & Services
- **Ollama API:** http://localhost:11434
- **DuckDuckGo API:** Search & Instant Answers
- **Wikipedia API:** MediaWiki
- **Open-Meteo API:** Weather Data
- **IP-API:** Geolocation

---

## 📁 Projektstruktur

```
/opt/liara/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # FastAPI App Entry
│   ├── api/
│   │   ├── routers/              # API Endpoints
│   │   │   ├── admin_health.py   # System Health Monitoring
│   │   │   ├── auth_router.py    # Authentication
│   │   │   ├── calendar_router.py
│   │   │   ├── chat.py           # Chat (sync)
│   │   │   ├── chat_streaming.py # Chat (SSE)
│   │   │   ├── external_router.py # Web Search
│   │   │   ├── gpu_router.py
│   │   │   ├── liara_router.py
│   │   │   ├── memory.py         # 4D Memory System
│   │   │   ├── mood_router.py
│   │   │   ├── notes_router.py
│   │   │   ├── ollama_router.py
│   │   │   ├── privacy_router.py
│   │   │   ├── tasks_router.py
│   │   │   ├── users_router.py
│   │   │   └── web_safety_router.py
│   │   ├── schemas/              # Pydantic Models
│   │   └── models/               # SQLAlchemy ORM
│   ├── core/
│   │   ├── config.py             # Environment Config
│   │   ├── database.py           # DB Connection
│   │   └── security.py           # JWT, Password Hashing
│   ├── liara_engine/             # AI Engine
│   │   ├── memory/               # Memory System
│   │   ├── nlp/                  # NLP Services
│   │   │   ├── embedding_service.py
│   │   │   ├── intent_detection.py
│   │   │   └── sentiment_analysis.py
│   │   └── actions/              # Task Automation
│   ├── dashboard/                # Dashboard Logic
│   │   └── info.py
│   └── system/                   # System Info
│
├── frontend/                     # Frontend (React + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx          # Authenticated Chat
│   │   │   ├── GuestChat.jsx     # Guest Chat
│   │   │   ├── SystemHealth.jsx  # Admin Health Dashboard
│   │   │   ├── MobileNav.jsx     # Mobile Navigation
│   │   │   ├── LegalPages.jsx    # Legal (4 components)
│   │   │   ├── PrivacySettings.jsx
│   │   │   ├── MoodDashboard.jsx
│   │   │   ├── Tasks.jsx
│   │   │   ├── Calendar.jsx
│   │   │   ├── Notes.jsx
│   │   │   ├── Config.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── SearchingIndicator.jsx
│   │   │   └── WebSearchResults.jsx
│   │   ├── services/
│   │   │   ├── api.js            # Authenticated API
│   │   │   └── guestApi.js       # Guest API
│   │   ├── styles/
│   │   │   └── halo-theme.css    # Design System
│   │   ├── App.jsx               # Main App Component
│   │   ├── App.css
│   │   └── main.jsx              # React Entry
│   ├── index.html
│   ├── vite.config.js            # Vite Config (Proxy)
│   ├── package.json
│   └── eslint.config.js
│
├── venv/                         # Python Virtual Environment
├── .env                          # Environment Variables
├── README.md                     # Hauptdokumentation
├── LIARA_FEATURES.md             # Feature-Übersicht (diese Datei)
└── docs/                         # Erweiterte Dokumentation
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    ├── DEPLOYMENT.md
    └── PRIVACY.md
```

---

## 🚀 Deployment

### Systemd Services

#### Backend
```ini
[Service]
Type=simple
User=mirko
WorkingDirectory=/opt/liara/app
ExecStart=/opt/liara/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8100
Restart=always
StandardOutput=append:/var/log/liara/backend.log
StandardError=append:/var/log/liara/backend.log
```

#### Frontend
```ini
[Service]
Type=simple
User=mirko
WorkingDirectory=/opt/liara/frontend
ExecStart=/usr/bin/npm run dev
Restart=always
StandardOutput=append:/var/log/liara/frontend.log
StandardError=append:/var/log/liara/frontend.log
```

### Nginx Config (Production)
```nginx
server {
    listen 80;
    server_name liara 192.168.178.50;

    location / {
        root /opt/liara/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Ports
- **8100:** FastAPI Backend (intern)
- **5173:** Vite Dev Server (Entwicklung)
- **80/443:** Nginx (Produktion)
- **5432:** PostgreSQL
- **6379:** Redis
- **7474/7687:** Neo4j
- **11434:** Ollama

---

## 🔒 Sicherheit

### Authentifizierung
- JWT mit RS256 (asymmetrisch)
- Access Token: 24h
- Refresh Token: 7 Tage
- HTTP-Only Cookies
- CSRF-Protection

### Passwörter
- bcrypt Hashing (12 Rounds)
- Min. 8 Zeichen
- Keine Klartextspeicherung

### API-Sicherheit
- Rate Limiting (100/h auth, 20/h guest)
- CORS-Policy (nur eigene Domain)
- Input-Validierung (Pydantic)
- SQL-Injection-Schutz (SQLAlchemy)
- XSS-Prevention (Content-Type Headers)

### Datenschutz
- Opt-in für Location
- Auto-Delete-Policies
- DSGVO-konformer Export
- Keine Third-Party-Tracking
- Lokale AI (kein Cloud-Upload)

---

## 📊 Performance

### Response Times
- **Chat (Streaming):** ~200ms bis erste Tokens
- **Web-Search:** ~1-3 Sekunden (API-abhängig)
- **Memory-Retrieval:** ~50-100ms (Redis Cache)
- **Database-Queries:** ~10-50ms (optimierte Indizes)

### Resource Usage (Typical)
- **CPU:** 15-30% (während Inferenz)
- **RAM:** 2-4 GB (mit Models geladen)
- **Disk:** ~5 GB (Models + DB)
- **Network:** Minimal (nur externe APIs)

### Optimierungen
- Redis-Caching (Session, Embeddings)
- Connection-Pooling (PostgreSQL)
- Lazy-Loading (React Components)
- SSE statt Polling
- Nginx-Gzip-Compression
- Vite Code-Splitting

---

## 🔄 Geplante Features

### Kurzfristig (Q1 2026)
- [ ] Voice-Input (Speech-to-Text)
- [ ] Exportfunktionen (Chat → PDF/Markdown)
- [ ] Dark/Light-Mode-Toggle
- [ ] Custom-Themes (User-definiert)
- [ ] Push-Notifications (Browser)

### Mittelfristig (Q2-Q3 2026)
- [ ] Multi-User-Chat (Räume)
- [ ] File-Upload & Analysis
- [ ] Cron-Jobs (Task-Automation)
- [ ] Email-Integration
- [ ] Mobile App (React Native)

### Langfristig (2027+)
- [ ] Plugin-System
- [ ] Custom-Model-Training
- [ ] Federation (Multi-Instance)
- [ ] Blockchain-Integration (Daten-Verifizierung)
- [ ] VR/AR-Interface

---

## 📝 Changelog

### Version 2.0 (3. Dezember 2025)
- ✨ **Halo/UNSC Design System** (komplettes UI-Redesign)
- ✨ **System Health Monitoring** (Admin-Dashboard)
- ✨ **Guest Streaming** (SSE für Gäste)
- ✨ **Mobile Navigation** (Hamburger-Menu)
- ✨ **Legal Pages** (4 Seiten: Impressum, Datenschutz, AGB, Cookies)
- ✨ **Privacy Settings** (Location Opt-in, Data Export/Delete)
- ✨ **Web Safety System** (URL-Risk-Analysis)
- 🔧 **Guest Message Limit:** 10 → 20
- 🔧 **Compact Spacing** (alle Komponenten überarbeitet)
- 🔧 **Systemd Auto-Start** (Backend + Frontend)
- 🐛 **Guest Chat 500 Error** behoben
- 🐛 **Browserslist Conflict** gelöst

### Version 1.0 (November 2025)
- 🎉 Initial Release
- Chat-System (Auth + Guest)
- 4D-Memory-System
- Task/Calendar/Notes
- Mood-Tracking
- Ollama-Integration
- PostgreSQL + Neo4j + Redis

---

## 🤝 Mitwirkende

**Hauptentwickler:**  
- Mirko (System-Architektur, Backend, Frontend, AI-Integration)

**KI-Assistenz:**  
- GitHub Copilot (Code-Unterstützung, Dokumentation)

**Inspirationen:**  
- Halo (Microsoft) - UI/UX-Design
- Cortana - Naming & Theme
- JARVIS (Iron Man) - Konzept
- Privacy-First-Bewegung - Datenschutz-Philosophie

---

## 📄 Lizenz

**Open Source** (Lizenz noch zu definieren)

Mögliche Optionen:
- MIT License (permissive)
- GPL v3 (copyleft)
- AGPL v3 (network-copyleft für SaaS)

**Aktuell:** Proprietär (private Nutzung)

---

## 📞 Support & Kontakt

- **Dokumentation:** `/opt/liara/docs/`
- **Issues:** GitHub (geplant)
- **Email:** (siehe Impressum)

---

**🌙 Made with ❤️ by Mirko • Powered by Ollama & Open Source**
