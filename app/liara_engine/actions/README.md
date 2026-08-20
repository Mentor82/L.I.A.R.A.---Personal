# Liara Actions - Self-Service Capabilities

Liara kann auf Anfrage verschiedene Aktionen selbstständig ausführen.

## Health Check Action 🔒 **Admin-only**

**Datei**: `health_check.py`

### Zugriffskontrolle

**NUR ADMINISTRATOREN** können Health Checks durchführen.
- Non-Admin User erhalten: "Systemstatus-Abfragen sind nur für Administratoren verfügbar."
- Prüfung erfolgt in `/api/routers/chat.py` vor Health Check Ausführung
- Basiert auf `UserRole.ADMIN` Check

### Funktionen

Liara kann ihren eigenen Systemstatus prüfen:

#### 1. Kompletter System-Check
**Admin fragt:**
- "Systemstatus?"
- "System Check?"
- "Health Check?"
- "Prüf das System"

**Liara antwortet mit:**
- Gesamtstatus (healthy/degraded/critical)
- Health Percentage (0-100%)
- Anzahl erfolgreicher Checks
- Zusammenfassung aller Services und Datenbanken

#### 2. System Load Check
**Admin fragt:**
- "System Load?"
- "System Auslastung?"
- "CPU und RAM Status?"
- "Server Load?"

**Liara antwortet mit:**
- CPU-Auslastung in %
- RAM-Auslastung in %
- Anzahl aktiver Verbindungen
- Aktueller Modus (SSE/SYNC)
- Reasoning für Modus-Wahl

#### 3. Datenbank Check
**Admin fragt:**
- "Datenbank Status?"
- "PostgreSQL Status?"
- "Database Check?"
- "Läuft die Datenbank?"

**Liara antwortet mit:**
- PostgreSQL Status
- Verbindungsinfo
- Pool-Status (falls verfügbar)

#### 4. Neo4j Check
**Admin fragt:**
- "Neo4j Status?"
- "Graph Database Check?"
- "Läuft Neo4j?"

**Liara antwortet mit:**
- Neo4j Status
- Anzahl Nodes im Graph
- Verbindungsinfo

#### 5. Ollama AI Check
**Admin fragt:**
- "Ollama Status?"
- "AI Service Check?"
- "Läuft Ollama?"

**Liara antwortet mit:**
- Ollama Service Status
- Verfügbare Modelle (falls gecached)
- Erreichbarkeit

### Technische Details

**Keywords für Health Check Detection:**
```python
HEALTH_CHECK_KEYWORDS = [
    'systemstatus', 'system status', 'system check', 'health check',
    'server status', 'backend status', 'api status',
    'datenbank status', 'database status', 'postgres status',
    'neo4j status', 'graph status', 'ollama status', 
    'ai status', 'service status', 'komponenten status',
    'system load', 'system auslastung', 'server load',
    'cpu auslastung', 'ram auslastung', 'speicher auslastung',
    'prüf system', 'check system', 'diagnose system',
    'läuft datenbank', 'läuft neo4j', 'läuft ollama'
]
```

**API Endpoints (intern):**
- `http://localhost:8100/admin/health/full` - Kompletter Health Check
- `http://localhost:8100/system/load` - System Load Metrics

**Response Format:**
```python
{
    "status": "success"|"error",
    "component": "Component Name",
    "data": {/* detailed data */},
    "message": "Human-readable summary"
}
```

### Integration

Der Health Check wird in `api/routers/chat.py` VOR der normalen Intent Detection ausgeführt:

```python
# 0. Health Check Intent Detection (vor normalem Intent)
if any(keyword in message_lower for keyword in HEALTH_CHECK_KEYWORDS):
    health_result = await check_system_health(component)
    return ChatResponse(
        response=health_result['message'],
        model_used="system-health",
        intent="health_check",
        action_result=health_result
    )
```

### Beispiel-Dialoge

**Dialog 1: Komplett-Check**
```
Admin: Systemstatus?
Liara: System: healthy (100%), 17/17 Checks OK
```

**Dialog 2: Load-Check**
```
Admin: System Auslastung?
Liara: CPU: 4.2%, RAM: 78.2%, Modus: sse
```

**Dialog 3: Komponenten-Check**
```
Admin: Datenbank Status?
Liara: PostgreSQL: healthy
```

**Dialog 4: Normale Konversation (KEIN Health Check)**
```
User: Wie geht es dir?
Liara: Mir geht es gut, danke der Nachfrage! Wie kann ich dir heute helfen? 😊
(→ Normale LLM-Antwort, kein Health Check)
```

### Vorteile

✅ **Self-Service**: Liara kann selbstständig Status prüfen
✅ **No Admin Required**: User müssen nicht Admin sein
✅ **Natural Language**: Normale Fragen, keine Commands
✅ **Fast Response**: Direkter API-Call, kein LLM nötig
✅ **Granular**: Gesamtsystem oder einzelne Komponenten
✅ **Cached**: System Load ist 2s gecached für Performance

### Sicherheit

- **Keine sensiblen Daten**: Nur Status-Informationen
- **Read-Only**: Keine Änderungen am System möglich
- **User-Isolation**: Jeder User kann nur seinen eigenen Status prüfen
- **Rate-Limited**: Durch allgemeines API Rate-Limiting geschützt

### Future Enhancements

Mögliche Erweiterungen:
- 📊 Historische Trends (CPU/RAM über Zeit)
- 🔧 Selbstheilende Aktionen (Restart bei Problemen)
- 📧 Proaktive Benachrichtigungen bei Degradation
- 🎯 Predictive Alerts (ML-basierte Vorhersagen)
- 📈 Performance Profiling (Bottleneck Detection)
