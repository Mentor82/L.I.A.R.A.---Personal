# Health Check Self-Service - Test Guide

## Feature: Liara kann ihren eigenen Status prüfen 🔒 **Admin-only**

**Version**: 1.0.1  
**Datum**: 5. Dezember 2025  
**Implementiert in**: `/app/liara_engine/actions/health_check.py`

---

## Übersicht

Liara kann jetzt auf natürliche Anfragen ihren Systemstatus selbstständig prüfen und berichten - **ABER NUR FÜR ADMINISTRATOREN**.

### Was ist neu?

✅ **Self-Service Health Checks**: Liara prüft eigenen Status  
✅ **Natural Language**: Keine Commands, normale Fragen  
✅ **Granular**: Gesamtsystem oder einzelne Komponenten  
✅ **Fast**: Direkter API-Call ohne LLM  
🔒 **Admin-only**: Nur Benutzer mit Admin-Rolle haben Zugriff  

---

## Zugriffskontrolle

### Admin-User
- ✅ Können alle Health Checks durchführen
- ✅ Erhalten detaillierte System-Metriken
- ✅ Können einzelne Komponenten abfragen

### Normale User
- ❌ Keine Health Check Berechtigung
- ✅ Erhalten freundliche Ablehnung:
  > "Systemstatus-Abfragen sind nur für Administratoren verfügbar. Als normaler User kannst du mich aber gerne fragen, wie ich dir helfen kann! 😊"
- ✅ Können weiterhin normale Chat-Funktionen nutzen

---

## Test-Szenarien

### Test 1: Kompletter System-Check

**Als:** Admin User (z.B. mirko mit Admin-Rolle)  
**Frage an Liara:**
```
Systemstatus?
```

**Erwartetes Ergebnis:**
```
System: healthy (100%), 17/17 Checks OK
```

**Alternative Fragen:**
- "System Check?"
- "Health Check?"
- "Prüf das System"

---

### Test 1b: Normale Konversation (KEIN Health Check)

**Als:** Beliebiger User (Admin oder Normal)  
**Frage an Liara:**
```
Wie geht es dir?
```

**Erwartetes Ergebnis:**
```
Mir geht es gut, danke der Nachfrage! Wie kann ich dir heute helfen? 😊
```

**Wichtig:** Dies triggert KEINEN Health Check mehr, sondern normale LLM-Konversation.  
Liara entscheidet selbst, ob sie die Frage als persönliches Befinden oder technischen Status interpretiert.

---

### Test 1c: Nicht-Admin versucht technischen Health Check ⛔alth Check ⛔

**Als:** Normaler User (NICHT Admin)  
**Frage an Liara:**
```
Systemstatus?
```

**Erwartetes Ergebnis:**
```
Systemstatus-Abfragen sind nur für Administratoren verfügbar. Als normaler User kannst du mich aber gerne fragen, wie ich dir helfen kann! 😊
```

**Response Struktur:**
```json
{
  "response": "Systemstatus-Abfragen sind nur für Administratoren verfügbar...",
  "model_used": "system-policy",
  "intent": "health_check_denied",
  "action_result": {
    "status": "forbidden",
    "message": "Admin privileges required"
  }
}
```

---

### Test 2: System Load Check (Admin-only)

**Frage an Liara:**
```
System Auslastung?
```

**Erwartetes Ergebnis:**
```
CPU: 4.2%, RAM: 78.2%, Modus: sse
```

**Alternative Fragen:**
- "System Load?"
- "CPU und RAM Status?"
- "Server Load?"

---

### Test 3: Datenbank Status

**Frage an Liara:**
```
Datenbank Status?
```

**Erwartetes Ergebnis:**
```
PostgreSQL: healthy
```

**Alternative Fragen:**
- "PostgreSQL Status?"
- "Database Check?"
- "Läuft die Datenbank?"

---

### Test 4: Neo4j Graph Database

**Frage an Liara:**
```
Neo4j Status?
```

**Erwartetes Ergebnis:**
```
Neo4j: healthy, Nodes: 1234
```

**Alternative Fragen:**
- "Wie geht es Neo4j?"
- "Graph Database Check?"

---

### Test 5: Ollama AI Service

**Frage an Liara:**
```
Ollama Status?
```

**Erwartetes Ergebnis:**
```
Ollama: healthy
```

**Alternative Fragen:**
- "AI Service Check?"
- "Funktioniert Ollama?"

---

## Technische Validierung

### 1. Backend Logs prüfen

```bash
tail -f /tmp/liara_access.log
```

**Erwartete Einträge bei Health Check:**
```
GET /system/load
GET /admin/health/full
```

### 2. Response Struktur prüfen

Öffne Browser Developer Console (F12) → Network Tab

**Erwartete Response:**
```json
{
  "response": "System: healthy (100%), 17/17 Checks OK",
  "model_used": "system-health",
  "intent": "health_check",
  "action_result": {
    "status": "success",
    "component": "System Health",
    "data": { ... },
    "message": "System: healthy (100%), 17/17 Checks OK"
  }
}
```

### 3. Performance Check

**Erwartung**: Antwort in < 500ms (kein LLM nötig)

```bash
curl -X POST http://localhost:8100/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Wie geht es dir?"}'
```

---

## Edge Cases & Fehlerbehandlung

### Test 6: Unbekannte Komponente

**Frage:**
```
Wie geht es XYZ?
```

**Erwartetes Ergebnis:**
- Kein Health Check ausgelöst (kein Keyword-Match)
- Normale LLM-Antwort von Liara

### Test 7: Backend offline

**Szenario**: Backend gestoppt  
**Erwartetes Ergebnis:**
```
Fehler beim Health Check: Connection refused
```

### Test 8: Timeout

**Szenario**: Backend überlastet, antwortet nicht  
**Erwartetes Ergebnis:**
```
Health Check Timeout - System antwortet nicht
```

---

## Keyword-Liste (für Entwickler)

Folgende Keywords triggern Health Check (nur technische/explizite Anfragen):

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
    'läuft datenbank', 'läuft neo4j', 'läuft ollama',
    'funktioniert datenbank', 'funktioniert neo4j'
]
```

**NICHT enthalten** (normale Konversation):
- "Wie geht es dir?" → LLM entscheidet
- "Läuft alles?" → LLM entscheidet  
- "Alles ok?" → LLM entscheidet
- Allgemeine "status", "cpu", "ram" ohne Kontext → LLM entscheidet

### Komponenten-Erkennung:

- **Database**: `datenbank`, `database`, `postgres`, `postgresql`
- **Neo4j**: `neo4j`, `graph`
- **Ollama**: `ollama`, `ai`, `model`
- **Load**: `load`, `auslastung`, `cpu`, `ram`, `speicher`
- **Default**: Kompletter System-Check

---

## Integration Points

### Backend-Dateien:

1. **Action Implementation**:
   - `/app/liara_engine/actions/health_check.py` (NEU)

2. **Chat Integration**:
   - `/app/api/routers/chat.py` (MODIFIZIERT)
   - Zeilen: Import + Health Check vor Intent Detection

3. **Health API Endpoints** (genutzt intern):
   - `GET /admin/health/full`
   - `GET /system/load`

### Frontend:

Keine Änderungen nötig - funktioniert im normalen Chat!

---

## Rollback Plan

Falls Probleme auftreten:

```bash
# 1. Backup aktueller Stand
cd /opt/liara
./create_backup.sh

# 2. Entferne Health Check Import aus chat.py
# Zeile 13: Entferne health_check Import
# Zeilen 438-471: Entferne Health Check Logic

# 3. Backend neu starten
./restart_backend.sh
```

---

## Success Criteria

✅ User kann "Wie geht es dir?" fragen → System-Status erhalten  
✅ User kann "CPU und RAM?" fragen → Load-Status erhalten  
✅ User kann "Datenbank Status?" fragen → DB-Status erhalten  
✅ Antwort in < 500ms  
✅ Keine Admin-Rechte erforderlich  
✅ Keine LLM-Calls für Health Check (Performance!)  
✅ Graceful Error Handling bei Backend-Problemen  

---

## Monitoring

### Metrics zu beobachten:

1. **Health Check Nutzung**:
   - Wie oft wird Feature genutzt?
   - Welche Komponenten werden am häufigsten geprüft?

2. **Response Times**:
   - Durchschnittliche Antwortzeit
   - 95th Percentile

3. **Error Rate**:
   - Timeouts
   - Connection Errors
   - Ungültige Komponenten

### Log-Suche:

```bash
# Alle Health Checks der letzten Stunde
grep "health_check" /tmp/liara_access.log | tail -n 100

# System Load Checks
grep "/system/load" /tmp/liara_access.log | tail -n 50
```

---

## Weitere Entwicklung

### Nächste Schritte (V1.1):

- [ ] Historische Trends (CPU/RAM über Zeit)
- [ ] Selbstheilende Aktionen (Auto-Restart bei Problemen)
- [ ] Proaktive Alerts bei Degradation
- [ ] Performance Profiling (Bottleneck Detection)
- [ ] Detailliertere Komponenten-Info

### Nice-to-Have:

- [ ] Grafische Visualisierung im Chat
- [ ] Export von Health Reports als PDF
- [ ] Scheduled Health Checks (täglich/wöchentlich)
- [ ] Integration mit externen Monitoring-Tools

---

## Fragen & Support

**Implementiert von**: GitHub Copilot  
**Dokumentation**: `/app/liara_engine/actions/README.md`  
**Tests**: Manuelle Tests via Chat-Interface  

**Bei Problemen:**
1. Backend Logs prüfen: `tail -f /tmp/liara_error.log`
2. Health API direkt testen: `curl http://localhost:8100/admin/health/full`
3. Debugging aktivieren in `health_check.py`
