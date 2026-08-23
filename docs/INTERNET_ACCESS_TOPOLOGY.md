# 🌐 Liara Internet-Zugriff Topologie

## Übersicht

> **Hinweis (Update):** Dieses Dokument beschrieb ursprünglich einen Stand
> ohne Tool-Calling und ohne automatischen Web-Zugriff im Chat. Das ist
> **nicht mehr aktuell** - Liara hat inzwischen einen echten Agent-Loop mit
> nativem Ollama-Tool-Calling (`app/api/routers/chat_streaming.py`,
> `app/services/tool_registry.py`/`tool_executor.py`), server-seitiges,
> sicheres URL-Fetching (`ProxySandbox`, s.u.), und seit Issue #4 Phase 1
> eine echte allgemeine Websuche via selbstgehostetem SearXNG statt nur
> DuckDuckGo Instant Answers. Die Abschnitte unten sind entsprechend
> korrigiert; "Erweiterungsmöglichkeiten" zeigt nur noch, was tatsächlich
> noch offen ist.

Ollama-Modelle selbst haben weiterhin keinen direkten Internet-Zugriff -
aber der Chat-Flow drumherum kann jetzt selbstständig (ohne dass der User
explizit einen separaten API-Call machen muss) entscheiden, ein Tool
aufzurufen, ein Ergebnis zu bekommen, und die Antwort darauf aufzubauen.

## Architektur-Ebenen

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React Frontend / Chat)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LIARA BACKEND (FastAPI)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Chat Router (/chat/stream)                    │  │
│  │                                                             │  │
│  │  • Empfängt User-Nachrichten                               │  │
│  │  • Verarbeitet System-Prompts                              │  │
│  │  • Leitet an Ollama weiter (mit tools=[...] für             │  │
│  │    tool-fähige Modelle)                                     │  │
│  │  • Agent-Loop: Modell kann web_search/wikipedia_search/     │  │
│  │    get_current_time selbst aufrufen (bis zu 3 Runden)       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │          External Router (/external)                       │  │
│  │                                                             │  │
│  │  ✅ /external/search        - Web-Suche                   │  │
│  │  ✅ /external/location      - IP-Geolocation              │  │
│  │  ✅ /external/weather       - Wetter-Daten                │  │
│  │                                                             │  │
│  │  Manuell durch User oder explizite API-Calls              │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                   ┌─────────┴─────────┐
                   ▼                   ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│   OLLAMA (Lokal)        │  │  EXTERNE WEB-SERVICES       │
│                         │  │                             │
│  • 10 Modelle           │  │  • DuckDuckGo API           │
│  • OFFLINE Inferenz     │  │  • Wikipedia API            │
│  • Kein Internet        │  │  • IP-Geolocation           │
│  • Nur lokale Daten     │  │  • OpenWeather API (opt.)   │
│                         │  │                             │
│  Models:                │  │  Alle Requests:             │
│  - llama3.2 (1b, 3b)    │  │  ✅ Privacy-First           │
│  - llama3.1 (8b)        │  │  ✅ User-Consent-basiert    │
│  - deepseek-r1 (7b)     │  │  ✅ Keine Tracking-Cookies  │
│  - qwen2.5 (7b)         │  │                             │
│  - gemma2 (9b)          │  │                             │
│  - mistral (7b)         │  │                             │
│  - phi3 (mini)          │  │                             │
│  - llava (7b) Vision    │  │                             │
│  - gpt-oss (20b)        │  │                             │
└─────────────────────────┘  └─────────────────────────────┘
```

---

## 🔒 Internet-Zugriff Mechanismen

### 1. **Ollama Modelle** (OFFLINE)
- **Status**: ❌ KEIN Internet-Zugriff
- **Fähigkeiten**:
  - Lokale Text-Generierung
  - Konversation mit gelerntem Wissen (bis Training-Cutoff)
  - Code-Generierung
  - Reasoning & Logik
  - Bildanalyse (LLaVA)
- **Limitierungen**:
  - Keine aktuellen Daten (Wetter, News, Aktienkurse)
  - Keine Echtzeit-Informationen
  - Kein Web-Browsing

### 2. **Web Search Service**
- **Endpoint**: `POST /external/search` (manuell) **und** das `web_search`
  Agent-Tool (automatisch, wenn das Modell es aufruft)
- **Provider, je nach `search_type`**:
  - `instant` (Standard): DuckDuckGo Instant Answer API - schnelle
    Fakten/Definitionen
  - `web`: selbstgehostetes **SearXNG** (`docker-compose.yml`, nur
    `127.0.0.1:8080`, nie öffentlich erreichbar) - echte Web-Suche mit
    mehreren Quellen für Recherche-Fragen, seit Issue #4 Phase 1. Die
    obersten Treffer werden zusätzlich per `ProxySandbox` real abgerufen
    und als Evidence-Records (URL, Titel, Domain, abgerufener Text)
    zurückgegeben, nicht nur ein Snippet.
  - `wikipedia`: Wikipedia-Suche
- **Privacy**:
  - ✅ Keine Tracking-Cookies
  - ✅ Kein User-Profiling
  - ✅ Nutzer-steuerbar: `allow_web_search` in den Privacy-Einstellungen
    schaltet `web_search`/`wikipedia_search` für den Agent-Pfad komplett ab
- **Integration**:
  - **Automatisch** möglich, wenn ein tool-fähiges Modell den Agent-Loop
    nutzt (kein separater API-Call durch den User nötig)
  - `/external/search` bleibt zusätzlich als manueller Endpoint bestehen

### 3. **Location Service** (OPTIONAL)
- **Endpoint**: `POST /external/location`
- **Provider**: IP-Geolocation APIs
- **Funktionen**:
  - Stadt/Region aus IP ermitteln
  - Timezone Detection
  - Koordinaten (optional)
- **Privacy**:
  - ✅ User-Consent erforderlich
  - ✅ Optional: LLM-Usage erlauben/verbieten
  - ✅ Speicherung nur mit Zustimmung

### 4. **Weather Service** (OPTIONAL)
- **Endpoint**: `POST /external/weather`
- **Provider**: OpenWeather API (falls konfiguriert)
- **Funktionen**:
  - Aktuelle Wetter-Daten
  - 5-Tage-Forecast
  - Location-basiert
- **Privacy**:
  - ✅ Location-Consent erforderlich

---

## 🚫 Was Liara (weiterhin) NICHT kann

1. ~~Automatischer Web-Zugriff in Chat~~ **- korrigiert, existiert jetzt:**
   tool-fähige Modelle können `web_search`/`wikipedia_search`/
   `get_current_time` selbst aufrufen (`app/services/tool_registry.py`,
   nativer Ollama `tools`-Support, geprüft via `/api/show`'s
   `capabilities`). Nicht tool-fähige Modelle (z.B. `phi3:mini`,
   `gemma2:9b`) bekommen weiterhin keine Tools angeboten.

2. **Aktuelle Informationen jenseits der Tool-Ergebnisse**
   - Ohne erfolgreichen Tool-Aufruf: nur Wissen bis Model-Training
   - Keine Echtzeit-Daten für Domänen ohne eigenes Tool (z.B. Aktienkurse)

3. ~~Link-Fetching / Scraping~~ **- korrigiert, existiert jetzt:**
   `ProxySandbox` (`app/services/web_safety/proxy_sandbox.py`) ruft
   Webseiten serverseitig sicher ab (GET-only, kein JS/Cookies, SSRF-
   geschützt seit Issue #4 Phase 1) und extrahiert Text/Überschriften/
   Tabellen. Seit Issue #4 Phase 1 nutzt `web_search(search_type="web")`
   das automatisch für die obersten Suchtreffer. Weiterhin nicht
   implementiert: PDF/Dokument-Downloads, JS-Rendering (Playwright) für
   Seiten, die ohne JavaScript keinen brauchbaren Inhalt liefern - bewusst
   auf später verschoben (Issue #4, "Non-goals for the first pass").

---

## ✅ Implementierte Internet-Features

### Web Search (DuckDuckGo)
```python
# Backend: /opt/liara/app/services/web_search_service.py
# Endpoint: POST /external/search
{
  "query": "Python asyncio tutorial",
  "search_type": "instant",  # oder "wikipedia"
  "language": "de"
}

# Response:
{
  "abstract": "...",
  "abstract_source": "Wikipedia",
  "abstract_url": "https://...",
  "related_topics": [...],
  "results": [...]
}
```

### Location Detection
```python
# Endpoint: POST /external/location
{
  "ip_address": "auto-detect",  # oder spezifische IP
  "save_with_consent": false
}

# Response:
{
  "city": "Berlin",
  "region": "Berlin",
  "country": "Germany",
  "timezone": "Europe/Berlin",
  "lat": 52.52,
  "lon": 13.40
}
```

### Weather Data
```python
# Endpoint: POST /external/weather
{
  "city": "Berlin",
  "language": "de"
}

# Response:
{
  "temperature": 5.2,
  "feels_like": 3.1,
  "humidity": 87,
  "description": "Bewölkt",
  "forecast": [...]
}
```

---

## 🔧 Erweiterungsmöglichkeiten (noch offen)

### ~~Option 1: Tool-Calling Integration~~ - implementiert
Native Ollama-`tools`, Agent-Loop mit bis zu 3 Extra-Runden, per-Modell
Fähigkeits-Check via `/api/show`. Siehe `app/api/routers/chat_streaming.py`.

### ~~Option 2: RAG mit Web-Scraping~~ - Kernstück implementiert (Issue #4 Phase 1)
`URL-Content-Fetcher` existiert bereits (`ProxySandbox`, BeautifulSoup-
basiert) und ist jetzt über `SearchBroker`+SearXNG an `web_search` (Agent-
Tool) angebunden. **Noch nicht gebaut** (Issue #4, spätere Phasen):
- Source-Policies (`first_party`/`official_docs`/`fresh`/...) als
  wählbare Suchmodi
- Freshness-Ranking (Datum-Gewichtung/Penalisierung statt reiner
  Relevanz-Reihenfolge)
- Eingebettete Zitat-UI im Frontend (aktuell rendert das Modell Quellen
  nur als normalen Markdown-Text/Links, keine dedizierten Source-Cards)
- Portierung von `SearchBroker`/Evidence-Schema ins Haupt-`L.I.A.R.A.`-Repo

### Option 3: Browser-Automation (weiterhin nicht implementiert)
**Erforderlich, falls gebraucht:**
1. Playwright/Selenium Integration - als Fallback NUR für JS-Seiten, wo
   der einfache HTTP-Fetch (`ProxySandbox`) keinen brauchbaren Inhalt
   liefert - bewusst kein Hard-Dependency der Standard-Suche (Issue #4)
2. Sandbox-Umgebung für sicheres Browsing
3. Screenshot → Vision API (LLaVA)
4. DOM-Parsing für strukturierte Daten

---

## 📊 Aktueller Status

| Feature | Status | Automatisch? | Privacy |
|---------|--------|--------------|---------|
| **Ollama Chat** | ✅ Aktiv | Ja | 🟢 Komplett lokal |
| **Web Search (Instant/DDG)** | ✅ Verfügbar | ✅ Ja (Agent-Tool) | 🟢 Privacy-First |
| **Web Search (allgemein/SearXNG)** | ✅ Verfügbar (Issue #4 Phase 1) | ✅ Ja (Agent-Tool) | 🟢 Privacy-First, `allow_web_search`-Toggle |
| **Location Detection** | ✅ Verfügbar | ❌ Nein (Consent-basiert) | 🟡 Consent erforderlich |
| **Weather API** | ✅ Verfügbar | ✅ Ja (Agent-Tool `get_weather`) | 🟢 Nur Stadtname, keine Nutzerdaten |
| **Tool-Calling / Agent-Loop** | ✅ Implementiert | Ja | 🟢 Per-Modell-Fähigkeits-Check |
| **Web-Scraping (ProxySandbox)** | ✅ Implementiert | ✅ Ja (über `web_search` Tool) | 🟢 SSRF-geschützt |
| **Browser-Automation** | ❌ Nicht implementiert | - | - |

---

## 🎯 Fazit

**Liara hat aktuell:**
- ✅ Leistungsstarke OFFLINE KI (Ollama-Modelle)
- ✅ Automatischer Tool-Aufruf im Chat für tool-fähige Modelle (Agent-Loop)
- ✅ Selbstgehostete, keyless Websuche (SearXNG) + sicheres Server-Fetching
  (ProxySandbox, SSRF-geschützt) für Recherche-Antworten mit echten Quellen
- ✅ Privacy-First Architektur, granular abschaltbar (`allow_web_search`)
- ❌ Noch keine Browser-Automation/JS-Rendering (bewusst nicht Teil der
  ersten Phase, siehe Issue #4)

---

## 🔐 Privacy-Garantien

1. **Ollama-Models**: 100% offline, keine Daten verlassen Server
2. **Web-Services**: Opt-In, User-Consent, keine Tracking-Cookies
3. **Location**: Nur mit expliziter Zustimmung, LLM-Usage optional
4. **Logs**: Nur lokal, keine Cloud-Sync
5. **User-Daten**: PostgreSQL lokal, keine externe Speicherung

---

**Erstellt**: 6. Dezember 2025
**Aktualisiert**: 23. August 2026 - Tool-Calling/Agent-Loop und
ProxySandbox/SearXNG-Websuche ergänzt (waren zuvor als "nicht
implementiert" beschrieben, siehe Issue #4)
**Version**: Liara v2.7+
**Autor**: AI Agent (Copilot)
