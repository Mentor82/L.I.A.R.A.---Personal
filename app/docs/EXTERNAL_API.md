# 🌍 External Information API - Privacy-Focused

## Overview

Die External Information API bietet **privacy-first** Web Search und Location Detection mit vollständiger Nutzer-Kontrolle.

**Philosophie:**
- ✅ **Opt-In statt Opt-Out**: Alle Features standardmäßig deaktiviert oder privacy-friendly
- ✅ **Keine IP-Speicherung**: Nur abgeleitete Location-Daten (Stadt/Region Ebene)
- ✅ **Granulare Kontrolle**: Separate Consent für jede Funktion
- ✅ **Auto-Delete**: Konfigurierbare Retention-Perioden
- ✅ **Privacy-APIs**: Nur Dienste ohne Tracking (DuckDuckGo, Wikipedia, Open-Meteo)

---

## 🔍 Web Search Endpoints

### POST `/external/search`

Führt privacy-focused Web-Suche durch.

**Request Body:**
```json
{
  "query": "Python FastAPI",
  "search_type": "instant",  // instant | wikipedia | weather
  "language": "de"           // de | en
}
```

**Search Types:**

1. **instant** - DuckDuckGo Instant Answer
   - Schnelle, präzise Antworten
   - Kein API Key erforderlich
   - Keine Cookies oder Tracking

2. **wikipedia** - Wikipedia Zusammenfassung
   - REST API v1
   - Unterstützt DE und EN
   - Extract + Thumbnail

3. **weather** - Wetter-Information
   - Open-Meteo API (kostenlos, kein API Key)
   - Aktuelle Temperatur, Luftfeuchtigkeit, Windgeschwindigkeit
   - Automatische Geocoding

**Response:**
```json
{
  "query": "Berlin",
  "search_type": "weather",
  "result": {
    "location": "Berlin",
    "country": "Deutschland",
    "temperature": 1.0,
    "humidity": 92,
    "wind_speed": 7.4,
    "timestamp": "2025-12-03T06:30"
  },
  "formatted_context": "Wetter-Information für Berlin:\nTemperatur: 1.0°C\n...",
  "timestamp": "2025-12-03T05:32:24.454597"
}
```

**Privacy:**
- Keine Speicherung ohne explizite Zustimmung (`store_search_history=true`)
- User-Agent: "Liara/1.0 (Privacy-focused AI Assistant)"
- Alle APIs ohne Tracking

---

## 📍 Location Detection Endpoints

### POST `/external/location/detect`

Erkennt Standort aus IP-Adresse (Privacy-Conscious).

**WICHTIG - Privacy:**
- ❌ IP-Adresse wird **NICHT gespeichert**
- ✅ Nur abgeleitete Location-Daten (Stadt/Region Ebene)
- ✅ Speicherung **NUR** mit expliziter Zustimmung
- ✅ Jederzeit widerrufbar

**Request Body:**
```json
{
  "ip_address": null,         // Auto-detect if null
  "save_with_consent": false  // true = speichern (benötigt Consent)
}
```

**Response:**
```json
{
  "status": "success",
  "country": "Germany",
  "region": "Bavaria",
  "city": "Munich",
  "timezone": "Europe/Berlin",
  "latitude": 48.1374,
  "longitude": 11.5755,
  "privacy_note": "IP address not stored, only derived location data",
  "consent_required": true,
  "saved": false
}
```

**Error Response (z.B. localhost):**
```json
{
  "error": "Location detection failed",
  "privacy_note": "No data collected",
  "saved": false
}
```

---

### GET `/external/location/current`

Holt gespeicherten Standort.

**Response:**
```json
{
  "country": "Germany",
  "region": "Bavaria",
  "city": "Munich",
  "timezone": "Europe/Berlin",
  "consent_given": true,
  "detected_at": "2025-12-03T05:30:00"
}
```

**Error (404):** Kein Standort gespeichert oder Consent nicht gegeben.

---

### POST `/external/location/consent`

Verwaltet Location Consent.

**Request Body:**
```json
{
  "grant_consent": true,     // true = erlauben, false = widerrufen
  "allow_llm_usage": true    // Erlaube Verwendung in LLM Context
}
```

**Response (Consent gegeben):**
```json
{
  "status": "consent_granted",
  "message": "Standort-Erkennung aktiviert",
  "allow_llm_usage": true
}
```

**Response (Consent widerrufen):**
```json
{
  "status": "consent_revoked",
  "message": "Standort-Daten gelöscht, Consent widerrufen"
}
```

**Effekt:**
- `grant_consent=true`: Aktiviert `allow_location_detection`, `allow_location_storage`, `share_location_with_llm`
- `grant_consent=false`: Löscht **alle** Location-Daten, deaktiviert alle Flags

---

## 🔒 Privacy Settings Endpoints

### GET `/external/privacy/settings`

Holt aktuelle Privacy-Einstellungen.

**Response:**
```json
{
  "allow_location_detection": false,
  "allow_location_storage": false,
  "share_location_with_llm": false,
  "allow_web_search": true,
  "store_search_history": false,
  "allow_search_for_training": false,
  "auto_delete_location_after_days": 30,
  "auto_delete_searches_after_days": 7,
  "updated_at": "2025-12-03 06:24:07"
}
```

**Default Values (Privacy-First):**
- Location: **DISABLED** (opt-in erforderlich)
- Web Search: **ENABLED** (aber privacy-focused APIs)
- Search History: **DISABLED**
- Training Data: **DISABLED**
- Auto-Delete: 30 Tage Location, 7 Tage Searches

---

### PATCH `/external/privacy/settings`

Aktualisiert Privacy-Einstellungen (granular).

**Request Body (alle optional):**
```json
{
  "allow_location_detection": true,
  "allow_location_storage": true,
  "share_location_with_llm": false,
  "allow_web_search": true,
  "store_search_history": true
}
```

**Response:**
```json
{
  "status": "updated",
  "message": "Privacy-Einstellungen aktualisiert"
}
```

**Granulare Kontrolle:**
- `allow_location_detection` - Erlaube Detection (nicht speichern)
- `allow_location_storage` - Erlaube Speicherung
- `share_location_with_llm` - Erlaube Nutzung in LLM Context
- `allow_web_search` - Erlaube Web-Suchen
- `store_search_history` - Speichere Such-Historie
- `allow_search_for_training` - Nutze Daten für Training

---

### DELETE `/external/privacy/delete-all-data`

Löscht **alle** externen Daten unwiderruflich.

**Response:**
```json
{
  "status": "deleted",
  "message": "Alle externen Daten wurden gelöscht",
  "timestamp": "2025-12-03T05:35:00"
}
```

**Was wird gelöscht:**
- ❌ Alle Location-Daten (`user_location_preferences`)
- ❌ Alle Such-Historie (`user_search_history`)
- ✅ Privacy-Settings werden auf Defaults zurückgesetzt

---

## 🎯 Integration in Chat

### Location Context

```python
# In chat endpoint, wenn share_location_with_llm=true:
location_service = get_location_service()
location = location_service.get_user_location(db, user_id)

if location:
    system_prompt += f"\n\nUser Location: {location['city']}, {location['country']}"
```

### Web Search

```python
# Intent Detection: Braucht User web search?
if "wetter" in user_message.lower():
    web_search = get_web_search_service()
    weather = web_search.get_weather_info(location['city'])
    context += web_search.format_for_llm(weather, 'weather')
```

---

## 📊 Database Schema

### `user_location_preferences`
```sql
user_id (FK users.id)
country, country_code, region, city
timezone, latitude, longitude
consent_given (BOOLEAN NOT NULL)
consent_timestamp
detected_at, updated_at
```

### `user_search_history`
```sql
user_id (FK users.id)
query, search_type, result_summary
stored_with_consent (BOOLEAN)
can_be_used_for_training (BOOLEAN)
searched_at, created_at
```

### `user_privacy_settings`
```sql
user_id (FK users.id)
allow_location_detection (DEFAULT false)
allow_location_storage (DEFAULT false)
share_location_with_llm (DEFAULT false)
allow_web_search (DEFAULT true)
store_search_history (DEFAULT false)
allow_search_for_training (DEFAULT false)
auto_delete_location_after_days (DEFAULT 30)
auto_delete_searches_after_days (DEFAULT 7)
created_at, updated_at
```

---

## 🔐 Privacy Compliance

### GDPR Konformität

1. **Informationspflicht**: Nutzer wird informiert, welche Daten erhoben werden
2. **Einwilligung**: Explizite Zustimmung erforderlich
3. **Widerrufsrecht**: `revoke_location_consent()` löscht alle Daten
4. **Datenminimierung**: Nur Stadt/Region Level, keine IPs
5. **Löschfristen**: Auto-Delete nach 7-30 Tagen

### API Privacy-Garantien

- **DuckDuckGo**: "We don't track you" (keine Cookies, keine Profile)
- **Wikipedia**: Open-Source, keine Tracker
- **Open-Meteo**: "Free weather API for non-commercial use, no API key needed"
- **ip-api.com**: Nur für Location Detection, IP nie gespeichert

---

## 🧪 Testing Examples

### Web Search
```bash
curl -X POST http://localhost:8000/external/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Deutschland", "search_type": "wikipedia", "language": "de"}'
```

### Location Detection
```bash
curl -X POST http://localhost:8000/external/location/detect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"save_with_consent": false}'
```

### Privacy Settings
```bash
# Get
curl -X GET http://localhost:8000/external/privacy/settings \
  -H "Authorization: Bearer $TOKEN"

# Update
curl -X PATCH http://localhost:8000/external/privacy/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"allow_location_detection": true, "store_search_history": true}'
```

---

## 🚀 Next Steps

1. **Frontend Integration**:
   - Privacy Consent Modal
   - Privacy Settings Page
   - Location Display in Profile
   - Search History View

2. **Auto-Delete Cron Job**:
   - Delete location data older than `auto_delete_location_after_days`
   - Delete searches older than `auto_delete_searches_after_days`

3. **Chat Integration**:
   - Add location context to system prompt (if consent given)
   - Auto-trigger web search based on intent detection
   - Store search results in memory if consent given

4. **Analytics** (Privacy-Preserving):
   - Aggregate stats (no individual tracking)
   - Popular search topics
   - Location distribution (country level only)
