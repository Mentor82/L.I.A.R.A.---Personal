# Liara - Vollständige Feature-Übersicht (Stand: Dezember 2025)

## 🎯 Core Features

### 1. Multi-Tier Chat System

#### **Registered User Chat**
- **Multi-Model Support**: 8+ Ollama Models (llama3.2:3b, qwen2.5, deepseek, etc.)
- **Streaming Responses**: Server-Sent Events (SSE) für Echtzeit-Antworten
- **Memory Integration**: 4D-Gedächtnissystem mit 20-Message Context Window
- **Intent Detection**: Automatische Kommandoerkennung (Create Task, Event, Note, Search)
- **Web Search**: DuckDuckGo, Wikipedia, Weather API, News
- **Location Services**: IP-basierte Lokalisierung mit Opt-In
- **Mood Integration**: Emotionale Kontexteinbindung in Antworten

#### **Guest Mode (No Registration)**
- **Streaming Chat**: SSE-basiert mit llama3.2:1b (schneller)
- **Web Search Enabled**: Wetter, Wikipedia, News verfügbar
- **Rate Limits**: 20 Nachrichten, 500 Zeichen max
- **No Persistence**: Keine Speicherung der Chat-Historie
- **Quick Access**: Sofort nutzbar ohne Account

---

## 🧠 4D Memory System

### **Architecture Overview**
The 4D Memory System provides multi-dimensional context storage for enhanced AI conversations and semantic recall.

### **1. Semantic Memory (PostgreSQL + pgvector)**
- **Embedding-Based Storage**: `semantic_metadata` table with 384-dimensional vectors
- **Model**: SentenceTransformer (sentence-transformers/all-MiniLM-L6-v2)
- **Content Types Stored**:
  - Chat messages
  - Tasks (with priority, tags, completion status)
  - Calendar events (with type, location, timestamps)
  - Notes (with category, tags, pinned status)
- **Metadata Extraction**:
  - Topics: Automatically extracted keywords
  - Intent: Classified intent (CHAT, SEARCH, CREATE, etc.)
  - Emotion: Detected emotion (neutral, joy, sadness, etc.)
  - Importance: Score 1-10
  - Content summary: Concise text representation
- **Search Capabilities**: 
  - Vector similarity search (cosine distance)
  - HNSW index for fast retrieval
  - Combined with filters (user_id, content_type, importance)

### **2. Graph Relations (Neo4j)**
- **Nodes**: Users, Messages, Tasks, Events, Notes, Topics
- **Relationships**: 
  - `MENTIONED_IN` - Entities referenced in messages
  - `RELATED_TO` - Semantic connections
  - `CREATED_FROM` - Tasks/Events/Notes derived from chat
  - `TRIGGERED_BY` - Actions triggered by intents
  - `BELONGS_TO` - User ownership
- **Pattern Analysis**: Mood patterns, productivity trends over time

### **3. Temporal Index (PostgreSQL)**
- **Sequence Tracking**: Order of user interactions
- **Time-based Queries**: "What did I do last week?"
- **Session Correlation**: Links related activities across sessions

### **4. Session Context (Redis)**
- **20-Message Window**: Sliding window for active conversations
- **Fast Access**: Sub-millisecond retrieval
- **Auto-Expire**: TTL-based session management (default: 1 hour)
- **User Isolation**: Separate contexts per user
- **Content**: Recent messages with embeddings for immediate context

### **Integration Flow**
1. User creates task/event/note via chat
2. Intent detected by `IntentDetector`
3. `ActionExecutor` creates item in PostgreSQL
4. `store_in_4d_memory()` called automatically:
   - Generates embedding
   - Extracts topics, intent, emotion
   - Stores in `semantic_metadata`
   - Creates Neo4j nodes/relationships
   - Updates Redis context
   - Adds to temporal index
5. AI can now recall and reference the item contextually

---

## 🔍 Web Search & External Services

### **Search Providers**
1. **DuckDuckGo** - General Web Search
2. **Wikipedia** - Faktenbasierte Abfragen
3. **Open-Meteo** - Wetter-API (keine API-Key nötig)
4. **News APIs** - Aktuelle Nachrichten

### **Location Services**
- **IP-basierte Lokalisierung**: ip-api.com
- **Opt-In Required**: User muss zustimmen
- **Auto-Delete**: Konfigurierbar (default: 30 Tage)
- **Privacy-First**: Keine Tracking-Cookies

### **Web Safety**
- **Content Filtering**: URL-basierte Risk-Scores
- **Rate Limiting**: Pro-User Limitierung
- **Logging**: Vollständige Audit-Trail
- **Statistics**: Admin-Dashboard Metrics

---

## 👑 Admin Panel (Responsive)

### **Layout & Navigation**
- **Desktop (>1024px)**: Sidebar Links (260px) mit Toggle
- **Tablet (768-1024px)**: Schmälere Sidebar (220px), collapsible
- **Mobile (<768px)**: Bottom Navigation (5 Hauptbereiche)

### **Dashboard** (`/admin`)
- **System Health Banner**: Live Health-Score mit Status-Farben
- **4 Statistik-Cards**: 
  - Benutzer (Total + Aktiv)
  - Chat-Nachrichten (Total + Heute)
  - AI Models (Anzahl geladen)
  - Speicher (GB genutzt/total)
- **Quick Actions**: 4 Schnellzugriff-Buttons
- **Activity Feed**: Letzte System-Events (Placeholder)

### **System Health** (`/admin/health`)
**Überwacht 30+ Komponenten:**
- **Ressourcen**: CPU, Memory, Disk (mit Thresholds: healthy <70%, warning 70-90%, critical >90%)
- **Services**: liara-backend, liara-frontend, nginx, postgresql, docker
- **Ports**: 8100, 5173, 80, 443, 5432, 6379, 7474, 7687, 11434
- **Docker Containers**: liara-redis, liara-neo4j
- **Databases**: PostgreSQL Connection + Table Count
- **Endpoints**: 4 HTTP Health-Checks
- **AI Services**: Ollama Availability + Model Count
- **Overall Score**: health_percentage = (passed/total) * 100
- **Auto-Refresh**: Toggle 30s Interval

### **Benutzerverwaltung** (`/admin/users`)
- **User Table**: Avatar, Name, E-Mail, Rolle, Status, Erstellt-Datum
- **Actions**:
  - ➕ Neuer User (Form: username, email, full_name, password, role)
  - ✏️ Rolle ändern (Dropdown: user/admin)
  - ✅ Aktivieren / 🚫 Deaktivieren
- **Responsive**: Desktop = Table, Mobile = Card-Stack

### **System-Konfiguration** (`/admin/config`)
**5 Konfigurationsbereiche:**

#### 1. AI & Model Settings
- Standard AI Model (Dropdown mit allen Ollama Models)
- Max Tokens (100-8000)
- Temperature Slider (0.0-1.0 mit Glüh-Effekt)
- System Prompt (Textarea für globalen Prompt)

#### 2. Rate Limits
- Gast-Nachrichten (1-100)
- Gast-Zeichenlänge (100-2000)
- User-Nachrichten (10-1000)
- Rate Limit Fenster (10-3600s)

#### 3. Features (Toggle Switches)
- 🔍 Web-Suche
- 📍 Standort-Dienste
- 👋 Gast-Modus
- 📝 Registrierung öffentlich

#### 4. Privacy & Retention
- Chat-Daten behalten (1-365 Tage)
- Such-Verlauf (1-90 Tage)
- Standort-Daten (1-90 Tage)
- Auto-Delete Toggle

#### 5. Ollama Config
- Host URL
- Timeout (30-600s)
- Auto-Pull beim Start

### **AI Models** (`/admin/models`) - Placeholder
- Geplant: Ollama Model Management
- Pull/Delete/List Models
- Storage Usage per Model

### **System Logs** (`/admin/logs`) - Placeholder
- Geplant: Live Log-Viewer
- Filter nach Service, Level, Zeitraum
- Export-Funktion

---

## 🔒 Privacy & DSGVO

### **Legal Pages**
1. **Impressum** - TMG §5 compliant
2. **Datenschutzerklärung** - DSGVO-konform mit Privacy-First Badge
3. **AGB** - Self-Hosted Open Source Terms
4. **Cookie-Richtlinie** - Essential Only (keine Tracking-Cookies)

### **Privacy Features**
- **No Cloud**: 100% Self-Hosted (Ollama lokal)
- **No Tracking**: Kein Google Analytics, kein Facebook Pixel
- **Essential Cookies Only**: liara_token, liara_guest_mode
- **Auto-Delete**: Konfigurierbare Daten-Retention
- **Opt-In Location**: User-Consent erforderlich
- **Data Export**: Vollständiger Daten-Export (geplant)

### **User Privacy Settings** (`/privacy`)
- **Location Consent**: Opt-In/Out Toggle
- **Current Location**: Anzeige + Clear-Button
- **Privacy Settings**: Konfiguration (geplant)
- **Data Export**: Alle User-Daten exportieren (geplant)
- **Delete All Data**: Account-Löschung (geplant)

---

## 📱 Responsive Design (Halo/UNSC Theme)

### **Design System**
- **Color Palette**:
  - Primary: #00D9FF (Cortana Cyan)
  - Secondary: #0A84FF (UNSC Blue)
  - Accent: #00FFB3 (Energy Shield)
  - Warning: #FFD60A
  - Danger: #FF453A
- **Typography**: Rajdhani, Orbitron, Roboto Mono
- **Spacing**: Compact (--space-xs: 0.25rem bis --space-2xl: 2rem)
- **Patterns**: Hexagon Grid Background, Scan-Line Animation

### **Responsive Breakpoints**
- **Desktop**: >1024px - Volle Sidebar + Grid Layouts
- **Tablet**: 768-1024px - Schmälere Sidebar, 2-Column Grids
- **Mobile**: <768px - Bottom Nav, Single Column, Hamburger Menu
- **Tiny**: <480px - Optimierte Font-Sizes, Stack Layouts

### **Mobile Navigation**
- **Hamburger Menu**: 3-Line Animation
- **Slide-In Panel**: Von rechts, 85% Breite (max 320px)
- **User Section**: Avatar, Name, Email, Guest-Badge
- **Navigation Items**: 8 Bereiche (gefiltert nach Guest/Admin)
- **Legal Section**: 4 Links (Impressum, Datenschutz, AGB, Cookies)
- **Logout Footer**: Button + Version Info

---

## 🗂️ Produktivität-Module

### **Tasks** (`/tasks`)
- **CRUD Operations**: Create, Read, Update, Delete
- **Priority System**: low 🟢, medium 🟡, high 🔴
- **Quick-Add Bar**: Smart Parsing (URGENT → high)
- **Daily/Weekly Views**: Filter nach Zeitraum
- **Completion Tracking**: Toggle mit Timestamp

### **Calendar** (`/calendar`)
- **Event Management**: Title, Description, Start/End DateTime
- **Conflict Detection**: Überschneidungs-Prüfung
- **Free-Slot Finding**: Nächste freie Zeitfenster
- **Views**: Today, Week, All Events

### **Notes** (`/notes`)
- **Rich Text**: Content mit Markdown-Support (geplant)
- **Categories**: Gruppierung nach Themen
- **Tags**: Multi-Tag Support (#hashtags)
- **Pin/Archive**: Wichtige Notes oben halten
- **Search**: Volltext-Suche (geplant)

### **Mood Dashboard** (`/mood`)
- **7D Visualization**: Radar-Chart für Emotionen
- **History Tracking**: Timeline mit Mood-Entries
- **Modifiers**: Boost/Reduce einzelne Dimensionen
- **Reset Function**: Auf Neutral zurücksetzen
- **State Suggestions**: Kontextuelle Empfehlungen

---

## 🔧 System-Integration

### **Systemd Services**
- **liara-backend.service**: FastAPI auf Port 8100
- **liara-frontend.service**: Vite Dev Server auf Port 5173
- **Auto-Start**: Enabled für multi-user.target
- **Logging**: /var/log/liara/{backend,frontend}.log
- **Restart Policy**: always mit 3s delay

### **nginx Production**
- **HTTPS**: Self-Signed oder Let's Encrypt
- **Reverse Proxy**: /api/ → localhost:8100
- **Static Files**: / → /opt/liara/frontend/dist
- **SSE Support**: proxy_buffering off für Streaming
- **Security Headers**: HSTS, X-Frame-Options, CSP
- **Caching**: 1 Jahr für Static Assets

### **Docker Containers**
- **liara-redis**: Port 6379, Volume redis_data
- **liara-neo4j**: Ports 7474/7687, Volume neo4j_data
- **Restart Policy**: unless-stopped
- **Health Checks**: Integriert im Admin Health Monitor

---

## 🔌 API Endpoints (Auswahl)

### **Authentication**
```
POST /auth/register       - Neue User Registration
POST /auth/login          - JWT Token erhalten
GET  /auth/me             - Current User Info
POST /auth/refresh        - Token refreshen
POST /auth/logout         - Session beenden
```

### **Chat**
```
POST /chat/message        - Synchrone Chat-Nachricht
POST /chat/stream         - SSE Streaming (User)
POST /chat/guest/message  - Guest Mode (sync)
POST /chat/guest/stream   - Guest Mode (SSE)
GET  /chat/models         - Verfügbare AI Models
GET  /chat/memory/status  - Memory System Status
```

### **Admin**
```
GET  /admin/health/full    - Vollständige Diagnostik
GET  /admin/health/summary - Dashboard-Übersicht
GET  /users/               - Alle User (Admin only)
PUT  /users/{id}/role      - Rolle ändern
PUT  /users/{id}/activate  - User aktivieren
```

### **Memory**
```
POST /memory/semantic_search - Ähnlichkeitssuche
GET  /memory/related         - Related Entities
GET  /memory/mood_patterns   - Emotion Trends
GET  /memory/context/{sid}   - Session Context
```

### **External**
```
POST /external/search            - Web-Suche
GET  /external/location/detect   - IP-Lokalisierung
POST /external/location/consent  - Opt-In/Out
```

### **Privacy**
```
GET  /privacy/settings      - User Privacy Config
POST /privacy/settings      - Update Config
GET  /privacy/export        - Daten exportieren
DELETE /privacy/all-data    - Alle Daten löschen
```

---

## 📊 Technologie-Stack

### **Backend**
- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 15, Neo4j 5.x, Redis 7+
- **ORM**: SQLAlchemy 2.0
- **Auth**: JWT (python-jose) + bcrypt
- **AI**: Ollama (llama.cpp)
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **HTTP Client**: httpx, requests

### **Frontend**
- **Framework**: React 19.2.0
- **Build Tool**: Vite 7.2.4
- **Router**: react-router-dom 7.1
- **State**: React Hooks (useState, useEffect, useContext)
- **HTTP**: Fetch API + SSE EventSource
- **Styling**: Custom CSS + Halo Theme Variables

### **Infrastructure**
- **OS**: Linux (Ubuntu 22.04+ / Debian 12+)
- **Web Server**: nginx 1.18+
- **Process Manager**: systemd
- **Containerization**: Docker 24+
- **Proxy**: nginx Reverse Proxy
- **SSL**: Let's Encrypt / Self-Signed

---

## 🎯 Roadmap & Geplante Features

### **Kurzfristig (Q1 2025)**
- [ ] AI Models Management UI (Pull/Delete/Storage)
- [ ] System Logs Live-Viewer
- [ ] Markdown Support für Notes
- [ ] Data Export Funktion (JSON/CSV)
- [ ] Account-Löschung (DSGVO-konform)
- [ ] Backend Config API (Settings speichern)

### **Mittelfristig (Q2 2025)**
- [ ] Multi-Language Support (i18n)
- [ ] Dark/Light Theme Toggle
- [ ] Voice Input (Speech-to-Text)
- [ ] File Upload für Chat
- [ ] Sharing-Funktion (Links teilen)
- [ ] Notifications (Browser Push)

### **Langfristig (Q3+ 2025)**
- [ ] Mobile Apps (React Native)
- [ ] Plugin System
- [ ] Custom Model Training
- [ ] Multi-User Collaboration
- [ ] Video/Audio Call Integration
- [ ] Blockchain-basierte Identität

---

## 📄 Lizenz & Credits

**Lizenz**: MIT  
**Autor**: Mirko  
**Projekt**: Liara Privacy-First AI Assistant  
**Inspiration**: Halo/UNSC Design (Microsoft), Cortana  
**Open Source**: Vollständig selbst-gehostet, keine Cloud-Abhängigkeiten

---

**Version**: 2.0.0  
**Stand**: Dezember 2025  
**Status**: Production Ready ✅
