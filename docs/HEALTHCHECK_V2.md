# Liara Healthcheck v2.0 - Dokumentation

## 🎯 Überblick

Das neue Healthcheck-Script v2.0 ist eine komplette Neuimplementierung mit:
- **Farb-kodierte Ausgabe** (Grün/Gelb/Rot)
- **Kategorisierte Checks** (10 Kategorien)
- **Detaillierte Statistiken** (Erfolgsrate, Summaries)
- **Performance-Metriken** (Response-Zeiten)
- **Security-Checks** (Firewall, SSL-Zertifikate)

## 🚀 Verwendung

### Schnellstart
```bash
cd /opt/liara
./healthcheck
```

oder

```bash
/opt/liara/scripts/liara_healthcheck_v2.sh
```

### Ausgabe nach Datei
```bash
./healthcheck > healthcheck_$(date +%Y%m%d).txt
```

## 📊 Check-Kategorien

### 1. **SYSTEM-RESSOURCEN**
- CPU Load & Cores
- RAM-Auslastung (mit Warnungen bei >75% / >90%)
- Disk-Auslastung (mit Fehlern bei >90%)
- System-Uptime

### 2. **SERVICE-STATUS**
Services:
- `liara-backend` (Gunicorn/Uvicorn)
- `liara-frontend` (Vite)
- `nginx`
- `postgresql`
- `ollama`

Zeigt:
- Laufstatus (aktiv/inaktiv)
- Startzeit
- Letzte Fehler (wenn Service down)

### 3. **PORT-VERFÜGBARKEIT**
Geprüfte Ports:
- **8100** - Backend (Gunicorn/Uvicorn)
- **5173** - Frontend (Vite Dev Server)
- **80** - Nginx (HTTP)
- **443** - Nginx (HTTPS)
- **5432** - PostgreSQL
- **11434** - Ollama API

### 4. **DATABASE-CONNECTIVITY**
- PostgreSQL-Version
- Verbindungstest
- Tabellen-Count
- Datenbankgröße
- User-Count

### 5. **API-ENDPOINTS**
Getestete Endpoints:
- `/` - Health-Check
- `/info` - System-Info
- `/dashboard/info` - Dashboard
- `/mood/status` - Mood-System
- `/sentiment/categories` - **NEU** Sentiment-Kategorien
- `/memory/status` - 4D-Memory

### 6. **AUTHENTICATION**
Test-Logins für:
- `admin`
- `user`
- `guest`

Mit Token-Extraktion (wenn jq verfügbar)

### 7. **OLLAMA AI-MODELS**
- Ollama-API-Status
- Liste aller verfügbaren Models
- Model-Namen-Extraktion

### 8. **NGINX-KONFIGURATION**
- Config-Validierung (`nginx -t`)
- Proxy-Test (API via Nginx)
- Redirect-Handling

### 9. **SECURITY-CHECKS**
- UFW Firewall-Status
- Erlaubte Verbindungen
- SSL-Zertifikate (LetsEncrypt)
- Ablaufdatum-Prüfung

### 10. **PERFORMANCE-METRIKEN**
- Backend Response-Zeit (in ms)
- Geschwindigkeits-Bewertung:
  - <100ms: Sehr schnell ✅
  - <500ms: Schnell ✅
  - <1000ms: Langsam ⚠️
  - >1000ms: Sehr langsam ❌
- Gunicorn Worker-Count

## 📈 Ausgabe-Format

### Farb-Kodierung
- 🟢 **[✓]** Grün - Erfolgreich
- 🟡 **[⚠]** Gelb - Warnung
- 🔴 **[✗]** Rot - Fehler
- 🔵 **[INFO]** Cyan - Information

### Beispiel-Ausgabe
```
═══════════════════════════════════════════════════
  SYSTEM-RESSOURCEN
═══════════════════════════════════════════════════

[INFO] CPU Load: 0.52 (Cores: 24)
[INFO] RAM: 9.2Gi / 24Gi (38%)
[✓] RAM-Auslastung normal: 38%
[INFO] Disk: 177G / 459G (39%)
[✓] Disk-Auslastung normal: 39%
[INFO] System Uptime: up 5 hours, 59 minutes
```

### Summary
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Erfolgreich:  18
  ⚠ Warnungen:    2
  ✗ Fehler:       7
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Erfolgsrate: 66.7%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 System ist gesund!
```

## 📝 Logfile

Alle Checks werden nach `/opt/liara/liara_healthcheck.log` geloggt.

### Logfile anzeigen
```bash
cat /opt/liara/liara_healthcheck.log
```

### Letzte Checks
```bash
tail -50 /opt/liara/liara_healthcheck.log
```

## ⚙️ Konfiguration

### Änderung der Test-Credentials
Im Script editieren (Zeile 21-25):
```bash
declare -A TEST_USERS=(
  [admin]="admin123"
  [user]="user123"
  [guest]="guest123"
)
```

### Änderung der Services
Im Script editieren (Zeile 28-34):
```bash
SERVICES=(
  "liara-backend"
  "liara-frontend"
  "nginx"
  "postgresql"
  "ollama"
)
```

### Neue API-Endpoints hinzufügen
Im Script editieren (Zeile 37-44):
```bash
declare -A API_ENDPOINTS=(
  [health]="/"
  [custom_endpoint]="/my/endpoint"
)
```

## 🔧 Fehlerbehandlung

### Exit-Codes
- **0** - Alle Checks erfolgreich
- **1** - Checks fehlgeschlagen (aber Script lief durch)

### Häufige Probleme

**Problem**: Port-Checks scheitern
```
[✗] Port 80 NICHT offen: Nginx (HTTP)
```
**Lösung**: 
```bash
sudo systemctl status nginx
sudo systemctl start nginx
```

**Problem**: Database-Verbindung fehlschlägt
```
[✗] Datenbankverbindung fehlgeschlagen
```
**Lösung**:
```bash
sudo systemctl status postgresql
# Prüfe pg_hba.conf
# Prüfe Credentials in Script
```

**Problem**: API-Endpoint Timeout
```
[✗] Endpoint 'health' (/): TIMEOUT/UNREACHABLE
```
**Lösung**:
```bash
sudo systemctl status liara-backend
journalctl -u liara-backend -n 50
```

## 📊 Vergleich v1.0 vs v2.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Farb-Ausgabe | ❌ | ✅ |
| Kategorisierung | ❌ | ✅ 10 Kategorien |
| Statistiken | Basis | ✅ Detailliert |
| Performance-Metriken | ❌ | ✅ Response-Zeit |
| Security-Checks | ❌ | ✅ Firewall + SSL |
| Ollama-Support | ❌ | ✅ Model-Liste |
| Sentiment-API | ❌ | ✅ Neu |
| Error-Handling | Basis | ✅ Verbessert |
| Lesbarkeit | OK | ✅✅ Excellent |

## 🎨 Anpassungen

### Farben deaktivieren (Plain Text)
```bash
./healthcheck | sed 's/\x1B\[[0-9;]*[a-zA-Z]//g'
```

### Nur Fehler anzeigen
```bash
./healthcheck | grep "✗"
```

### Nur Summary
```bash
./healthcheck | tail -20
```

## 🔄 Automatisierung

### Cron-Job (täglich um 6 Uhr)
```bash
0 6 * * * /opt/liara/healthcheck >> /opt/liara/healthcheck_daily.log 2>&1
```

### Systemd-Timer
```bash
# /etc/systemd/system/liara-healthcheck.timer
[Unit]
Description=Liara Healthcheck Timer

[Timer]
OnCalendar=daily
OnBootSec=5min

[Install]
WantedBy=timers.target
```

## ✨ Neue Features in v2.0

1. **Live-Sentiment-Analyse Check** ✨
   - Testet `/sentiment/categories` Endpoint
   - Zeigt Verfügbarkeit der neuen Sentiment-API

2. **Verbesserte Error-Messages**
   - Zeigt letzte Fehler direkt
   - Konkrete Fix-Vorschläge

3. **Performance-Monitoring**
   - Response-Zeit-Messung in Millisekunden
   - Automatische Bewertung (schnell/langsam)

4. **Security-Audit**
   - Firewall-Status
   - SSL-Zertifikats-Ablauf

5. **Erfolgsrate-Berechnung**
   - Prozentuale Erfolgsquote
   - Gesundheits-Status: 🎉 / ⚠️ / ❌

## 🆘 Support

Bei Problemen:
1. Logfile prüfen: `/opt/liara/liara_healthcheck.log`
2. Service-Status: `systemctl status <service>`
3. Backend-Logs: `journalctl -u liara-backend -n 100`

---

**Version**: 2.0  
**Erstellt**: 2025-12-04  
**Script**: `/opt/liara/scripts/liara_healthcheck_v2.sh`  
**Symlink**: `/opt/liara/healthcheck`
