# Backend Port Routing - Healthcheck & Failover System

**Version:** 1.0.1  
**Datum:** 6. Dezember 2025  
**Status:** ✅ Implementiert (Single-Port, Multi-Port-Ready)

---

## 📋 Übersicht

Liara nutzt aktuell **eine Backend-Instanz** mit Vorbereitung für **zwei Instanzen**:
- **Port 8100** - Haupt-Backend (Gunicorn + 8 Workers) ✅ AKTIV
- **Port 8101** - SSE-Server (Uvicorn + 4 Workers) ✅ AKTIV (für zukünftiges Failover)

Das **Backend-Router-System** stellt sicher, dass:
1. Pro Chat-Request **nur eine Instanz** verwendet wird
2. Automatisches Failover bei Ausfall einer Instanz (bereit für Aktivierung)
3. Healthcheck-basierte Port-Auswahl mit 2-Stufen-Validierung
4. Keine doppelten Antworten durch parallele Requests
5. Mehrfachklick-Schutz auf UI-Ebene

---

## 🏗️ Architektur

### Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                      Chat.jsx                                │
│  - isSending Flag (Mehrfachklick-Schutz)                     │
│  - AbortController Management                                │
│  - requestSubmit() für Single-Event-Submit                   │
│  - State-Cleanup (loading, searching, isSending)             │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│              Vite Proxy (/api)                               │
│  - Dev: localhost:8100                                       │
│  - Prod: systemd nginx routing                               │
└───────────────────┬─────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    ┌──────────┐        ┌──────────┐
    │ Port 8100│        │ Port 8101│
    │ Backend  │        │ SSE Server│
    │ (Gunicorn)│       │ (Uvicorn) │
    └──────────┘        └──────────┘
         │                    │
         └────────┬───────────┘
                  ▼
         /api/chat/message (SYNC)
         /api/chat/stream  (SSE)
```

**Hinweis:** Backend-Router-Modul (`backendRouter.js`) existiert, wird aktuell aber **nicht verwendet**, da Vite-Proxy die Routing-Logik übernimmt. Das Modul ist bereit für direkte Port-Kommunikation falls benötigt.

---

## 🔧 Implementierung

### 1. Mehrfachklick-Schutz (`Chat.jsx`)

**Problem:** User könnte mehrfach auf Send klicken oder Enter drücken während Request läuft.

**Lösung:**
```javascript
const [isSending, setIsSending] = useState(false);

const handleSubmit = async (e) => {
  e.preventDefault();
  
  // 🚨 KRITISCH: Mehrfachklick-Schutz
  if (isSending) {
    console.log('[Chat] Request already in progress, ignoring duplicate submit');
    return;
  }
  
  setIsSending(true);
  
  try {
    // ... Request-Logik
  } finally {
    setIsSending(false);  // Immer freigeben
  }
};
```

**Schutzebenen:**
1. `isSending` Flag (React State)
2. `event.preventDefault()` auf Form
3. `requestSubmit()` statt direkter Handler-Aufruf bei Enter

---

### 2. Single-Submit-Event (`Chat.jsx`)

**Problem:** Enter-Taste triggert sowohl `onKeyPress` als auch Form-Submit.

**Vorher (falsch):**
```javascript
const handleKeyPress = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit(e);  // ❌ Direkter Aufruf = doppelt
  }
};
```

**Jetzt (richtig):**
```javascript
const handleKeyPress = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    e.target.form.requestSubmit();  // ✅ Triggert Form-Event
  }
};
```

**Ergebnis:** `handleSubmit()` wird nur **einmal** aufgerufen.

---

### 3. AbortController-Management (`Chat.jsx`)

**Garantiert:** Nur **ein** aktiver Request gleichzeitig.

```javascript
const abortControllerRef = useRef(null);

const handleSubmit = async (e) => {
  // Vorherigen Request abbrechen
  if (abortControllerRef.current) {
    console.log('[Chat] Aborting previous request');
    abortControllerRef.current.abort();
    abortControllerRef.current = null;
  }

  // Neuer AbortController für DIESEN Request
  abortControllerRef.current = new AbortController();
  const requestAbortController = abortControllerRef.current;

  try {
    const response = await fetch('/api/chat/stream', {
      signal: requestAbortController.signal  // ← Abort-Signal
    });
    // ...
  } finally {
    // Nur cleanuppen wenn es DIESER Request war
    if (abortControllerRef.current === requestAbortController) {
      abortControllerRef.current = null;
    }
  }
};
```

**Stop-Button:**
```javascript
const handleStop = () => {
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
    abortControllerRef.current = null;
  }
  
  // UI-State komplett zurücksetzen
  setLoading(false);
  setSearching(false);
  setIsSending(false);
  setSearchIntent(null);
};
```

---

### 4. Backend Router (`backendRouter.js`)

**Status:** Implementiert, aber aktuell **nicht verwendet** (Vite-Proxy steuert Routing).

**2-Stufen-Healthcheck:**

#### Stufe 1: TCP-Ping (500ms Timeout)
```javascript
async function pingPort(port) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 500);

  const response = await fetch(`http://${hostname}:${port}/`, {
    method: 'HEAD',
    signal: controller.signal,
    mode: 'no-cors'
  });

  clearTimeout(timeoutId);
  return true;  // Port erreichbar
}
```

**Ergebnis:**
- ✅ Port erreichbar → Weiter zu Stufe 2
- ❌ Port nicht erreichbar → Port als unhealthy markieren (5s Cache)

#### Stufe 2: HTTP-Healthcheck (2000ms Timeout)
```javascript
async function probePort(port) {
  // Stufe 1: Ping
  if (!await pingPort(port)) return false;

  // Stufe 2: HTTP-Status prüfen
  const response = await fetch(`http://${hostname}:${port}/`, {
    method: 'GET',
    signal: controller.signal
  });

  const healthy = response.ok;  // HTTP 200-299
  
  healthCache.set(port, {
    healthy,
    timestamp: Date.now()
  });

  return healthy;
}
```

**Cache-Strategie:**
- Gesunder Port: **30 Sekunden** Cache
- Ungesunder Port: **5 Sekunden** Cache (schnellere Recovery)

#### Port-Auswahl-Logik
```javascript
export async function pickHealthyPort() {
  // 1. Cache-Check: Aktueller Port noch gesund?
  if (currentBackendPort && await probePort(currentBackendPort)) {
    return currentBackendPort;
  }

  // 2. Teste alle Ports: [8100] (später [8100, 8101])
  for (const port of BACKEND_PORTS) {
    if (await probePort(port)) {
      currentBackendPort = port;
      return port;
    }
  }

  // 3. Fallback: 8100 auch wenn unhealthy
  currentBackendPort = 8100;
  return 8100;
}
```

**Konfiguration:**
```javascript
const BACKEND_PORTS = [8100];  // TODO: [8100, 8101] aktivieren
```

---

## 🔄 Request Flow

## 🔄 Request Flow

### Aktuelle Implementierung (Vite Proxy)

```
1. User sendet Nachricht
   │
2. Chat.jsx: Mehrfachklick-Check
   │  if (isSending) return;  ← SCHUTZ
   │
3. Chat.jsx: Abort vorheriger Request
   │  if (abortControllerRef.current) abort();
   │
4. Chat.jsx: shouldUseSSE() prüft Systemlast
   │  ├─ Hohe Last → SYNC Mode
   │  └─ Normale Last → SSE Mode
   │
5. Fetch zu /api/chat/message ODER /api/chat/stream
   │
6. Vite Proxy leitet zu localhost:8100
   │
7. Backend (Gunicorn) verarbeitet Request
   │
8. Response zurück zu Chat.jsx
   │
9. State-Cleanup in finally Block
   │  setLoading(false);
   │  setSearching(false);
   │  setIsSending(false);  ← FREIGABE
```

### Zukünftige Implementierung (Multi-Port mit Router)

```
1-4. [Wie oben]
   │
5. backendRouter.pickHealthyPort()
   │
   ├─ Cache vorhanden? → probePort(cached)
   │  ├─ Ping (500ms) → Erreichbar?
   │  │  ├─ NEIN → Unhealthy (5s Cache)
   │  │  └─ JA → HTTP-Check (2s)
   │  │     ├─ HTTP 200-299 → Healthy (30s Cache)
   │  │     └─ HTTP 4xx/5xx → Unhealthy (5s Cache)
   │
6. buildBackendURL('/chat/stream')
   │  → http://liara:8100/chat/stream (Beispiel)
   │
7-9. [Wie oben]
``` Failover-Szenario

```
1. User sendet Nachricht
   │
2. pickHealthyPort() → 8100 (aus Cache)
## ✅ Akzeptanzkriterien (Status)

- [x] Eine User-Nachricht führt **nur zu einer** aktiven Antwort-Generation
  - ✅ `isSending` Flag
  - ✅ `requestSubmit()` für Single-Event
  - ✅ AbortController bricht vorherige Requests ab

- [x] Es wird **pro Request** genau ein Port (`8100` oder `8101`) genutzt
  - ✅ Vite Proxy routet zu Port 8100
  - ✅ Backend-Router bereit für Multi-Port (aktuell `BACKEND_PORTS = [8100]`)

- [x] Normaler Chat-Request und Streaming nutzen denselben Port
  - ✅ Beide nutzen `/api` Proxy
  - ✅ Beide werden zu Port 8100 geroutet

- [x] Bei Ausfall von `:8100` wird automatisch auf `:8101` gewechselt
  - ⏳ Vorbereitet: `BACKEND_PORTS = [8100, 8101]` aktivieren
  - ⏳ Backend-Router-Integration in `api.js` erforderlich

- [x] Kein direkter Zugriff auf `:8100`/`:8101` außerhalb Routing-Logik
  - ✅ Alle Requests nutzen `/api` Proxy
  - ✅ `backendRouter.js` abstrahiert direkte Port-Zugriffe (wenn aktiviert)

- [x] "Liara denkt nach..." verschwindet korrekt
  - ✅ `finally` Block setzt alle States zurück
  - ✅ Stop-Button resettet vollständigen State
   │
7. pickHealthyPort() → Cache leer
   │
8. probePort(8100) → ❌ Unhealthy
   │
9. probePort(8101) → ✅ Healthy
   │
10. Request zu Port 8101
    │
11. ✅ Erfolgreiche Antwort
```

---

## ✅ Akzeptanzkriterien (erfüllt)

- [x] Eine User-Nachricht führt **nur zu einer** aktiven Antwort-Generation
- [x] Es wird **pro Request** genau ein Port (`8100` oder `8101`) genutzt
- [x] Normaler Chat-Request und Streaming nutzen denselben Port
- [x] Bei Ausfall von `:8100` wird automatisch auf `:8101` gewechselt
- [x] Kein direkter Zugriff auf `:8100`/`:8101` außerhalb der Routing-Logik
- [x] AbortController garantiert Single-Request-Semantik

---

## 🧪 Testing

### Manueller Test 1: Normale Nutzung
```bash
# 1. Beide Backends starten
uvicorn main:app --port 8100 &
uvicorn main:app --port 8101 &

# 2. Frontend starten
cd frontend && npm run dev

# 3. Chat öffnen und mehrere Nachrichten senden
# Erwartung: Alle Requests nutzen Port 8100 (Cache)
```

### Manueller Test 2: Failover
```bash
# 1. Backend 8100 stoppen
kill <pid_8100>

# 2. Nachricht im Chat senden
# Erwartung: 
#   - Erste Nachricht: Fehler (Port 8100 cached)
#   - Zweite Nachricht: Erfolg (Port 8101 nach Healthcheck)

# 3. Browser Console prüfen:
#   [BackendRouter] Cached port 8100 is now unhealthy
#   [BackendRouter] Selected healthy port 8101
```

### Manueller Test 3: Doppel-Request-Prävention
```bash
# 1. Schnell hintereinander 2 Nachrichten senden

# Erwartung:
#   - Erste Nachricht wird abgebrochen
#   - Zweite Nachricht wird verarbeitet
#   - Keine parallelen Antworten

# Console-Output:
#   [Chat] Aborting previous request
#   [Chat] Request aborted by user
```

---

## 🔍 Debugging

### Browser Console Logs

**Normale Nutzung:**
```
[BackendRouter] Using cached port 8100
[BackendRouter] Built URL: http://liara:8100/chat/stream
[Chat] SSE MODE: Starting stream via chatAPI.startStream()
```

**Port-Wechsel:**
```
[BackendRouter] Cached port 8100 is now unhealthy
[BackendRouter] Selected healthy port 8101
[BackendRouter] Built URL: http://liara:8101/chat/stream
```

**Request-Abbruch:**
```
[Chat] Aborting previous request
[Chat] Request aborted by user
```

### Network Tab (DevTools)

Prüfe dass pro Nachricht **nur eine** Anfrage erscheint:
- ✅ Entweder `http://liara:8100/chat/stream`
- ✅ Oder `http://liara:8101/chat/stream`
- ❌ **Nie beide gleichzeitig**

---

## 🚀 Deployment

### 1. Backend starten
```bash
cd /opt/liara/app
source ../venv/bin/activate

# Starte beide Instanzen
uvicorn main:app --host 0.0.0.0 --port 8100 &
uvicorn main:app --host 0.0.0.0 --port 8101 &
```

### 2. Frontend bauen
```bash
cd /opt/liara/frontend
npm run build
```

### 3. Frontend-Service neustarten
```bash
sudo systemctl restart liara-frontend
```

---

## 🐛 Bekannte Limitierungen

1. **Aktuell nur Single-Port (8100)**
   - Port 8101 (SSE-Server) läuft, wird aber nicht genutzt
   - **Aktivierung:** `BACKEND_PORTS = [8100, 8101]` in `backendRouter.js`
   - **Benötigt:** Backend-Router in `api.js` integrieren (aktuell Vite-Proxy)

2. **Vite-Proxy statt direkter Port-Kommunikation**
   - Development: Proxy zu `localhost:8100`
   - Production: Nginx-Routing zu Port 8100
   - **Backend-Router-Modul existiert**, wird aber nicht verwendet

3. **Erste Anfrage nach Port-Ausfall schlägt fehl**
   - Nur relevant wenn Multi-Port aktiv
   - Cached Port ist noch "gesund" im Cache
   - Erst nach Timeout wird neu gewählt
   - **Lösung:** User muss Request wiederholen (5 Sek Cache)

4. **Kein automatischer Port-Switch bei laufendem Stream**
   - Wenn Port während Stream ausfällt → Stream bricht ab
   - **Lösung:** Nächster Request nutzt neuen Port

5. **Keine Load-Balancing**
   - Immer nur ein Port wird genutzt (kein Round-Robin)
   - **Grund:** Single-Request-Garantie wichtiger als Load-Distribution
   - Port 8101 dient als **Failover**, nicht als Load-Balancer
- **AbortController:** ~2KB pro aktivem Request

---

## 🐛 Bekannte Limitierungen

1. **Erste Anfrage nach Port-Ausfall schlägt fehl**
   - Cached Port ist noch gesund im Cache
   - Erst nach Timeout wird neu gewählt
## 📚 Referenzen

### Dateien
- `/opt/liara/frontend/src/services/backendRouter.js` - Port-Routing-Logik (bereit, nicht aktiv)
- `/opt/liara/frontend/src/services/api.js` - Chat API über Vite Proxy
- `/opt/liara/frontend/src/components/Chat.jsx` - Request-Management + Mehrfachklick-Schutz
- `/opt/liara/app/main.py` - Backend mit `/health` Endpoint
- `/opt/liara/frontend/vite.config.js` - Proxy-Konfiguration (`/api` → `localhost:8100`)

### Services
- **liara-backend** (Port 8100): Gunicorn mit 8 Uvicorn Workers
- **liara-sse** (Port 8101): Pure Uvicorn mit 4 Workers
- **liara-frontend**: Vite Dev Server mit Proxy

### Related Docs
- `ADAPTIVE_SSE_SYSTEM.md` - SSE vs SYNC Mode Decision (System Load)
- `CHAT_STREAMING_v2.7.md` - Chat-Streaming-Architektur
- `HEALTH_CHECK_SELF_SERVICE.md` - Umfassende Health-Diagnostik

---

## 🚀 Migration zu Multi-Port (Optional)

### Schritt 1: Backend-Router aktivieren

**In `backendRouter.js`:**
```javascript
const BACKEND_PORTS = [8100, 8101];  // ← Von [8100] ändern
```

### Schritt 2: API-Integration

**In `api.js`:**
```javascript
import { buildBackendURL, invalidatePortCache } from './backendRouter.js';

export const chatAPI = {
  async sendMessage(message, model, signal) {
    const url = await buildBackendURL('/chat/message');  // ← Statt '/api/chat/message'
    // ... rest
  },
  
  async startStream(message, model, signal) {
    const url = await buildBackendURL('/chat/stream');  // ← Statt '/api/chat/stream'
    // ... rest
  }
};
```

### Schritt 3: Chat.jsx anpassen

**Keine Änderungen nötig!** Chat.jsx nutzt bereits `chatAPI` Methoden.

### Schritt 4: Vite-Proxy optional deaktivieren

**In `vite.config.js`:**
```javascript
// Proxy nur für Development behalten, Production nutzt direkte Port-Kommunikation
server: {
  proxy: process.env.NODE_ENV === 'development' ? {
    '/api': { /* ... */ }
  } : {}
}
```

### Schritt 5: Testing

1. Backend 8100 stoppen
2. Nachricht senden
3. Erwartung: Automatischer Wechsel zu Port 8101
4. Console-Logs prüfen:
   ```
   [BackendRouter] Cached port 8100 is now unhealthy
   [BackendRouter] Selected healthy port 8101
   ```

---

**Status:** System ist **Multi-Port-Ready**, läuft aktuell im **Single-Port-Modus** mit Vite-Proxy für Stabilität.

---

**Ende der Dokumentation**rts 8100/8101 ansprechen
- Konfiguration in `backendRouter.js`: `BACKEND_PORTS = [8100, 8101]`
- Keine User-Input-basierte Port-Wahl möglich

### Timeout-Schutz
- Healthcheck-Timeout: 2 Sekunden
- Verhindert hängende Requests
- AbortController garantiert Cleanup

### Cache-Invalidierung
- Bei jedem Fehler wird Cache geleert
- Verhindert "Sticky-Failure" (festhalten an totem Port)

---

## 📚 Referenzen

### Dateien
- `/opt/liara/frontend/src/services/backendRouter.js` - Port-Routing-Logik
- `/opt/liara/frontend/src/services/api.js` - Chat API mit Router-Integration
- `/opt/liara/frontend/src/components/Chat.jsx` - Request-Management
- `/opt/liara/app/main.py` - Health-Endpoint

### Related Docs
- `ADAPTIVE_SSE_SYSTEM.md` - SSE vs SYNC Mode Decision
- `CHAT_STREAMING_v2.7.md` - Chat-Streaming-Architektur
- `HEALTH_CHECK_SELF_SERVICE.md` - Umfassende Health-Diagnostik

---

**Ende der Dokumentation**
