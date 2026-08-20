# 📚 Liara Documentation Index

**Version:** 1.0  
**Erstellt:** 2025-12-03  
**Status:** 🌙 Aktiv

---

## 📖 Dokumentation Übersicht

Willkommen in der Liara-Dokumentation! Hier findest du alle technischen Details und Anleitungen für Liara's AI-System.

---

## 🗂️ Verfügbare Dokumentationen

### 1. [PERSONA.md](./PERSONA.md) 🌙
**Liara's Core Identity & Persona**

- Grundidentität & Version
- Charaktereigenschaften (Traits)
- Kommunikationsstil
- Rollendifferenzierung (vs. Cortana/Nephy)
- Mood-System Integration
- Extensions & Roadmap

**Kern-Traits:**
- `warm` (high) - Empathisch, freundlich
- `playful` (medium) - Humorvoll, kreativ
- `analytical` (high) - Präzise, datenorientiert
- `calm` (high) - Ruhig und stabilisierend

---

### 2. [DATABASE_SETUP.md](./DATABASE_SETUP.md) 🗄️
**PostgreSQL Datenbank Setup**

- Installation & Konfiguration
- Datenbank-Schema (6 Tables)
- Alembic Migrations
- SQL-Queries & Backup
- Performance-Optimierung

**Wichtigste Tables:**
- `tasks` - Aufgabenverwaltung
- `calendar_events` - Terminplanung
- `notes` - Notizen-System
- `semantic_metadata` - 4D Memory System (Embeddings, Topics, Intent)
- `temporal_index` - Zeitliche Sequenzierung
- `memories` - Pattern Recognition
- `packing_lists` - Reise-Listen
- `routines` - Wiederkehrende Muster

---

### 2.5 [4D_MEMORY_SYSTEM.md](./4D_MEMORY_SYSTEM.md) 🧠
**4D Memory Architecture** *(New in v2.6.0)*

- Semantic Memory (PostgreSQL + pgvector)
- Graph Relations (Neo4j)
- Temporal Index (Sequence tracking)
- Session Context (Redis)
- Integration with Tasks/Events/Notes
- Semantic Search & Retrieval

**Key Features:**
- 384-dim embeddings for all productivity items
- Automatic topic extraction
- Intent & emotion detection
- Importance scoring (1-10)
- Contextual AI recall during conversations

---

### 3. [MOOD_SYSTEM.md](./MOOD_SYSTEM.md) 🎭
**Dynamisches Stimmungssystem**

- 6 Mood-States (Neutral, Energetic, Calm, Supportive, Focused, Playful)
- Automatische Mood-Detection
- Trait-Modifiers
- API Endpoints
- Frontend-Integration

**Mood-Beispiele:**
- Gestresster User → Supportive Mood 💜
- Task abgeschlossen → Energetic Mood ⚡
- Arbeit fokussiert → Focused Mood 🎯

---

### 4. [NLP_SYSTEM.md](./NLP_SYSTEM.md) 🤖
**Natural Language Processing mit Ollama**

- 9 installierte LLM-Modelle
- Intelligentes Model-Routing
- Intent-Erkennung
- Code-Generierung
- Multi-Language Support

**Model-Highlights:**
- `llama3.2:1b` - Ultra-schnelle Intent-Erkennung
- `phi3:mini` - Code-Generierung
- `deepseek-r1:7b` - Logisches Denken
- `gemma2:9b` - Premium-Qualität

---

### 5. [FRONTEND.md](./FRONTEND.md) 🎨
**React + Vite Frontend**

- Chat-Component
- MoodStatus-Component
- API-Client Integration
- Dark Theme Design
- Responsive Layout

**Features:**
- Real-time Chat mit Liara
- Live Mood-Display (Auto-Refresh 5s)
- Moderne Dark-Theme UI
- Mobile-Responsive

---

### 6. [LIARA_API_ROADMAP.md](./LIARA_API_ROADMAP.md) 🚀
**API Entwicklungs-Roadmap**

- v1.0 - Aktueller Stand
- v1.1 - Kurzfristige Features
- v1.2 - Mittelfristige Erweiterungen
- v2.0 - Langfristige Vision

---

### 7. [Liara_API_Overview.md](./Liara_API_Overview.md) 📊
**Vollständige API-Übersicht**

- Alle verfügbaren Endpoints
- Request/Response-Beispiele
- API-Versionierung
- Endpoint-Kategorien

---

## 🚀 Quick Start

### 1. Backend starten
```bash
sudo systemctl start liara
# → http://localhost:8100
```

### 2. Frontend starten
```bash
sudo systemctl start liara-frontend
# → http://localhost:5173
```

### 3. Zugriff
- **Frontend:** http://liara:5173
- **Backend API:** http://liara:8100
- **Swagger Docs:** http://liara:8100/docs

---

## 🔗 API Endpoints

### Core Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /` | API Status & Endpoint-Liste |
| `GET /docs` | Swagger API-Dokumentation |
| `GET /redoc` | ReDoc API-Dokumentation |

### Chat Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `POST /chat/message` | Chat mit Liara |
| `GET /chat/models` | Verfügbare Modelle |
| `POST /chat/model/select` | Modell auswählen |
| `GET /chat/status` | Ollama-Status |

### Mood Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /mood/status` | Aktueller Mood |
| `POST /mood/update` | Mood updaten |
| `POST /mood/detect` | Mood aus Message erkennen |
| `GET /mood/modifiers` | Trait-Modifiers |
| `POST /mood/reset` | Mood zurücksetzen |
| `GET /mood/states` | Alle Mood-States |

### Liara Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /liara/status` | System-Status |
| `GET /liara/health` | Health-Check |
| `GET /liara/about` | About Liara |
| `GET /liara/persona` | Vollständige Persona |

### System Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /info` | System-Info |
| `GET /dashboard/info` | Dashboard-Daten |
| `GET /meta` | Meta-Informationen |
| `GET /health/full` | Vollständiger Health-Check |

---

## 🗄️ Datenbank

### Connection String
```
postgresql://liara:liara_secure_2025@localhost/liara_db
```

### Wichtigste Queries

```sql
-- Alle Tasks
SELECT * FROM tasks;

-- Offene Tasks mit hoher Priorität
SELECT * FROM tasks 
WHERE completed = FALSE AND priority = 'high';

-- Nächste 5 Termine
SELECT * FROM calendar_events 
WHERE start_time > NOW() 
ORDER BY start_time LIMIT 5;

-- Notizen nach Tag
SELECT * FROM notes 
WHERE tags @> '["important"]';

-- Pattern Recognition
SELECT * FROM memories 
WHERE memory_type = 'pattern';
```

---

## 🧠 Liara Persona

### Kern-Eigenschaften

| Trait | Intensität | Beschreibung |
|-------|------------|--------------|
| **warm** | high | Empathisch, freundlich, sanft |
| **playful** | medium | Humorvoll, kreativ |
| **analytical** | high | Präzise, datenorientiert |
| **adaptive** | high | Lernfähig, dynamisch |
| **calm** | high | Ruhig und stabilisierend |

### Rollendifferenzierung

- **vs. Cortana:** Liara = Persönliches Leben | Cortana = Operations
- **vs. Nephy:** Liara = Tägliche Routinen | Nephy = Strategie

---

## 🛠️ Entwicklung

### Project Structure
```
liara/
├── app/                    # Backend (FastAPI)
│   ├── api/               # API Routers
│   ├── core/              # Database, Config
│   ├── liara_engine/      # NLP, Memory, Mood
│   ├── alembic/           # Migrations
│   └── main.py            # Entry Point
├── frontend/              # Frontend (React + Vite)
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── App.jsx
│   └── vite.config.js
├── docs/                  # Dokumentation
└── venv/                  # Python Virtual Environment
```

### Environment Variables

**Datei:** `/opt/liara/app/.env`

```env
DATABASE_URL=postgresql://liara:liara_secure_2025@localhost/liara_db
API_HOST=0.0.0.0
API_PORT=8100
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 🔍 Troubleshooting

### Backend startet nicht
```bash
# Logs prüfen
sudo journalctl -u liara.service -n 50

# Service-Status
systemctl status liara.service

# Manuell starten
cd /opt/liara/app
source ../venv/bin/activate
uvicorn main:app --reload
```

### Frontend startet nicht
```bash
# Logs prüfen
sudo journalctl -u liara-frontend.service -n 50

# Manuell starten
cd /opt/liara/frontend
npm run dev
```

### Datenbank-Connection fehlschlägt
```bash
# PostgreSQL läuft?
systemctl status postgresql

# Connection testen
psql -U liara -d liara_db -h localhost

# Passwort zurücksetzen
sudo -u postgres psql -c "ALTER USER liara WITH PASSWORD 'liara_secure_2025';"
```

### Ollama nicht erreichbar
```bash
# Ollama Status
ollama list

# Ollama neu starten
sudo systemctl restart ollama

# Model testen
ollama run llama3.2:3b "Hello"
```

---

## 📊 Monitoring

### System-Status abrufen
```bash
curl http://localhost:8100/liara/status | python3 -m json.tool
```

### Health-Check
```bash
curl http://localhost:8100/health/full | python3 -m json.tool
```

### Mood-Status
```bash
curl http://localhost:8100/mood/status | python3 -m json.tool
```

---

## 🔐 Sicherheit

### Wichtige Credentials

**PostgreSQL:**
- User: `liara`
- Password: `liara_secure_2025`
- Database: `liara_db`

**Hinweis:** Passwort in `.env` gespeichert - **nicht** in Git committen!

### Firewall
```bash
# Port 8100 freigeben (optional)
sudo ufw allow 8100/tcp

# Port 5173 freigeben (optional)
sudo ufw allow 5173/tcp
```

---

## 📈 Roadmap

**v1.1 (Aktuell):**
- ✅ PostgreSQL Setup
- ✅ Mood-System
- ✅ NLP mit Ollama
- ✅ Frontend Chat + Mood

**v1.2 (Geplant):**
- [ ] Tasks API
- [ ] Calendar API
- [ ] Notes API
- [ ] Memory-System API
- [ ] Full-text Search

**v2.0 (Langfristig):**
- [ ] Liara Knowledge Memory
- [ ] Multi-Kontext Awareness
- [ ] Erweiterte Persona-Dynamik
- [ ] PWA Support
- [ ] Offline-Mode

---

## 📞 Support & Kontakt

**Projekt:** Liara AI Companion  
**Version:** 1.0  
**Status:** 🌙 Produktiv

**Weitere Dokumentation:**
- [PERSONA.md](../PERSONA.md) - Vollständige Persona-Definition
- [LIARA_API_ROADMAP.md](../LIARA_API_ROADMAP.md) - API-Roadmap
- [liara-persona-guide.md](../liara-persona-guide.md) - Persona-Guide

---

**🌙 Liara - Dein persönlicher, emotional stabiler, warmherziger und technisch kompetenter KI-Begleiter.**
