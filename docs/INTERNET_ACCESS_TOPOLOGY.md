# 🌐 Liara Internet-Zugriff Topologie

## Übersicht

Liara besitzt **KEINEN direkten Internet-Zugriff über Ollama**, aber hat **externe Web-Services** über eigene API-Endpunkte.

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
│  │  • Leitet an Ollama weiter                                 │  │
│  │  • KEIN automatischer Web-Zugriff                          │  │
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

### 2. **Web Search Service** (OPTIONAL)
- **Endpoint**: `POST /external/search`
- **Provider**: DuckDuckGo Instant Answer API
- **Funktionen**:
  - Instant Answers (Fakten, Definitionen)
  - Wikipedia-Suche
  - Related Topics
  - Keine personalisierte Suche
- **Privacy**:
  - ✅ Keine Tracking-Cookies
  - ✅ Kein User-Profiling
  - ✅ IP-Anonymisierung möglich
- **Integration**:
  - **NICHT automatisch** in Chat integriert
  - User muss explizit Web-Suche anfordern
  - Separate API-Calls notwendig

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

## 🚫 Was Liara NICHT kann (ohne Erweiterung)

1. **Automatischer Web-Zugriff in Chat**
   - Ollama-Modelle können NICHT selbstständig das Internet durchsuchen
   - Kein "Tool-Calling" oder "Function-Calling" für Web-Requests
   - User muss explizit externe Services aufrufen

2. **Aktuelle Informationen**
   - Ohne Web-Service: Nur Wissen bis Model-Training (ca. 2023-2024)
   - Keine Echtzeit-Daten (Aktienkurse, Sportergebnisse, News)

3. **Link-Fetching / Scraping**
   - Kein automatisches Abrufen von Webseiten-Inhalten
   - Keine PDF/Dokument-Downloads aus dem Web
   - URL-Inhalte müssen manuell bereitgestellt werden

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

## 🔧 Erweiterungsmöglichkeiten

### Option 1: Tool-Calling Integration
**Erforderlich:**
1. Model mit Tool-Calling Support (z.B. `llama3.1:8b` mit Functions)
2. Custom Prompt Template mit Tool-Definitionen
3. Parser für Tool-Requests im Chat-Stream
4. Automatische Ausführung + Rückgabe an Model

**Beispiel-Flow:**
```
User: "Was ist das Wetter in Berlin?"
  ↓
Liara (Ollama): [TOOL_REQUEST: weather_search(city="Berlin")]
  ↓
Backend: Führt /external/weather aus
  ↓
Liara (Ollama): "Das Wetter in Berlin ist bewölkt, 5°C..."
```

### Option 2: RAG mit Web-Scraping
**Erforderlich:**
1. URL-Content-Fetcher (BeautifulSoup, Playwright)
2. Text-Extraktion & Chunking
3. Embedding-Generierung (Ollama Embeddings)
4. Vector-DB Integration (bereits vorhanden: 4D Memory)
5. Kontext-Injection in Chat

### Option 3: Browser-Automation
**Erforderlich:**
1. Playwright/Selenium Integration
2. Sandbox-Umgebung für sicheres Browsing
3. Screenshot → Vision API (LLaVA)
4. DOM-Parsing für strukturierte Daten

---

## 📊 Aktueller Status

| Feature | Status | Automatisch? | Privacy |
|---------|--------|--------------|---------|
| **Ollama Chat** | ✅ Aktiv | Ja | 🟢 Komplett lokal |
| **Web Search (DDG)** | ✅ Verfügbar | ❌ Nein | 🟢 Privacy-First |
| **Location Detection** | ✅ Verfügbar | ❌ Nein | 🟡 Consent erforderlich |
| **Weather API** | ✅ Verfügbar | ❌ Nein | 🟡 Consent erforderlich |
| **Tool-Calling** | ❌ Nicht implementiert | - | - |
| **Web-Scraping** | ❌ Nicht implementiert | - | - |
| **Browser-Automation** | ❌ Nicht implementiert | - | - |

---

## 🎯 Fazit

**Liara hat aktuell:**
- ✅ Leistungsstarke OFFLINE KI (10 Ollama-Modelle)
- ✅ OPTIONALE Web-Services (User-gesteuert)
- ✅ Privacy-First Architektur
- ❌ KEINE automatische Internet-Integration in Chat

**Für automatischen Internet-Zugriff in Chat wäre erforderlich:**
1. Tool-Calling Support im Chat-Flow
2. Automatische Erkennung von Web-Anfragen
3. Transparente Tool-Execution
4. Result-Rückgabe an Model für finale Antwort

---

## 🔐 Privacy-Garantien

1. **Ollama-Models**: 100% offline, keine Daten verlassen Server
2. **Web-Services**: Opt-In, User-Consent, keine Tracking-Cookies
3. **Location**: Nur mit expliziter Zustimmung, LLM-Usage optional
4. **Logs**: Nur lokal, keine Cloud-Sync
5. **User-Daten**: PostgreSQL lokal, keine externe Speicherung

---

**Erstellt**: 6. Dezember 2025  
**Version**: Liara v2.7+  
**Autor**: AI Agent (Copilot)
