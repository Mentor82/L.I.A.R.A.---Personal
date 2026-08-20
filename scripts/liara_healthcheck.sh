#!/bin/bash


# Liara System Health, API, Frontend & Nginx Check Script
# Führt Health-Check, System-Check, API-Login-Test, Nginx-Status, Frontend- und Backend-Port-Check durch
# Logging nach /opt/liara/liara_healthcheck.log

LOGFILE="/opt/liara/liara_healthcheck.log"

# Altes Logfile löschen, damit nur aktueller Durchlauf enthalten ist
if [ -f "$LOGFILE" ]; then
  rm "$LOGFILE"
fi
API_URL="http://localhost:8100"

# Test-Logins
declare -A TEST_USERS
TEST_USERS[admin]="admin123"
TEST_USERS[user]="user123"
TEST_USERS[guest]="guest123"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}


log "--- Liara Healthcheck gestartet ---"

# Backend-Status (systemctl)
log "Backend-Status (systemctl status gunicorn):"
if systemctl status gunicorn 1>>"$LOGFILE" 2>&1; then
  log "Gunicorn läuft."
else
  log "[Fehler] Gunicorn läuft nicht oder ist nicht installiert!"
fi

# Backend-Logauszug (journalctl)
log "Letzte 20 Zeilen Gunicorn-Log (journalctl -u gunicorn):"
sudo journalctl -u gunicorn -n 20 --no-pager 2>>"$LOGFILE" | tee -a "$LOGFILE"

# Backend-Verzeichnis und main.py prüfen
BACKEND_DIR="/opt/liara/app"
if [ -d "$BACKEND_DIR" ]; then
  log "Backend-Verzeichnis $BACKEND_DIR vorhanden."
  if [ -f "$BACKEND_DIR/main.py" ]; then
    log "main.py im Backend-Verzeichnis gefunden."
  else
    log "[Fehler] main.py im Backend-Verzeichnis fehlt!"
  fi
else
  log "[Fehler] Backend-Verzeichnis $BACKEND_DIR fehlt!"
fi

# Datenbankverbindung testen (psql)
log "Teste Datenbankverbindung für User 'liara':"
PGPASSWORD="liaras_own" psql -U liara -h localhost -d liara_db -c '\l' 1>>"$LOGFILE" 2>&1
if [ $? -eq 0 ]; then
  log "Datenbankverbindung erfolgreich."
else
  log "[Fehler] Datenbankverbindung fehlgeschlagen! Prüfe Zugangsdaten und DB-Status."
fi

# 0. Nginx-Status
log "Nginx Status (systemctl):"
if systemctl status nginx 1>>"$LOGFILE" 2>&1; then
  log "Nginx läuft."
else
  log "[Fehler] Nginx läuft nicht oder ist nicht installiert!"
fi

# 0b. Nginx Konfigurationstest
log "Nginx Konfigurationstest:"
if nginx -t 1>>"$LOGFILE" 2>&1; then
  log "Nginx-Konfiguration OK."
else
  log "[Fehler] Nginx-Konfiguration fehlerhaft!"
fi

# 0c. Nginx Port-Check (80, 443)
for PORT in 80 443; do
  if sudo lsof -i :$PORT | grep -q LISTEN; then
    log "Port $PORT wird von: $(sudo lsof -i :$PORT | grep LISTEN | awk '{print $1, $2, $9}')"
  else
    log "[Warnung] Port $PORT nicht offen (Nginx?)"
  fi
done

# 0d. Backend-Port-Check (8100)
if sudo lsof -i :8100 | grep -q LISTEN; then
  log "Backend-Port 8100 offen: $(sudo lsof -i :8100 | grep LISTEN | awk '{print $1, $2, $9}')"
else
  log "[Fehler] Backend-Port 8100 nicht offen! (Gunicorn/Uvicorn?)"
fi

# 0e. Frontend-Port-Check (5173)
if sudo lsof -i :5173 | grep -q LISTEN; then
  log "Frontend-Port 5173 offen: $(sudo lsof -i :5173 | grep LISTEN | awk '{print $1, $2, $9}')"
else
  log "[Warnung] Frontend-Port 5173 nicht offen! (Vite/React?)"
fi

# 0f. Frontend-Check (HTTP)
FRONTEND_URL="http://localhost:5173"
log "Frontend-Check: $FRONTEND_URL"
FRONTEND_RESP=$(curl -s -w "\n%{http_code}" "$FRONTEND_URL" 2>>"$LOGFILE")
FRONTEND_BODY=$(echo "$FRONTEND_RESP" | head -n -1)
FRONTEND_CODE=$(echo "$FRONTEND_RESP" | tail -n1)
if [ "$FRONTEND_CODE" = "200" ]; then
  log "Frontend erreichbar. Antwort: $FRONTEND_BODY"
else
  log "[Warnung] Frontend nicht erreichbar! HTTP $FRONTEND_CODE. Antwort: $FRONTEND_BODY"
fi

# 0g. Nginx-Proxy-Check (API via Nginx)
NGINX_API_URL="http://localhost/api/info"
log "Nginx-Proxy-Check (API via Nginx): $NGINX_API_URL"
NGINX_API_RESP=$(curl -s -w "\n%{http_code}" "$NGINX_API_URL" 2>>"$LOGFILE")
NGINX_API_BODY=$(echo "$NGINX_API_RESP" | head -n -1)
NGINX_API_CODE=$(echo "$NGINX_API_RESP" | tail -n1)
if [ "$NGINX_API_CODE" = "200" ]; then
  log "API via Nginx erreichbar. Antwort: $NGINX_API_BODY"
else
  log "[Warnung] API via Nginx nicht erreichbar! HTTP $NGINX_API_CODE. Antwort: $NGINX_API_BODY"
fi

# 1. System-Check: Speicher, CPU, Disk
log "System-Check: Speicher, CPU, Disk-Auslastung:"
if ! free -h 2>>"$LOGFILE" | tee -a "$LOGFILE"; then
  log "[Fehler] Speicherabfrage fehlgeschlagen!"
fi
log "CPU-Last:"
if ! uptime 2>>"$LOGFILE" | tee -a "$LOGFILE"; then
  log "[Fehler] CPU-Last-Abfrage fehlgeschlagen!"
fi
log "Festplattenplatz:"
if ! df -h 2>>"$LOGFILE" | tee -a "$LOGFILE"; then
  log "[Fehler] Festplattenplatz-Abfrage fehlgeschlagen!"
fi

# 2. Health-Check Endpoint
log "API Health-Check: $API_URL/"
HEALTH=$(curl -s -w "\n%{http_code}" "$API_URL/" 2>>"$LOGFILE")
HEALTH_BODY=$(echo "$HEALTH" | head -n -1)
HEALTH_CODE=$(echo "$HEALTH" | tail -n1)
if [ "$HEALTH_CODE" != "200" ]; then
  log "❌ API Health-Check fehlgeschlagen! HTTP $HEALTH_CODE. Antwort: $HEALTH_BODY"
  log "[Tipp] Prüfe, ob Gunicorn/Uvicorn läuft, ob main.py korrekt importiert wird und ob Firewall/Netzwerk Ports blockiert. Siehe auch: 'sudo systemctl status gunicorn' und Logs im Backend-Ordner."
else
  log "API Antwort: $HEALTH_BODY"
fi

# 3. Systeminfo Endpoint
log "API Systeminfo: $API_URL/info"
SYSINFO=$(curl -s -w "\n%{http_code}" "$API_URL/info" 2>>"$LOGFILE")
SYSINFO_BODY=$(echo "$SYSINFO" | head -n -1)
SYSINFO_CODE=$(echo "$SYSINFO" | tail -n1)
if [ "$SYSINFO_CODE" != "200" ]; then
  log "❌ Systeminfo-Endpoint fehlgeschlagen! HTTP $SYSINFO_CODE. Antwort: $SYSINFO_BODY"
  log "[Tipp] Prüfe, ob der API-Server korrekt läuft und /info-Route implementiert ist. Logs und Status von Gunicorn/Uvicorn checken."
else
  log "Systeminfo Antwort: $SYSINFO_BODY"
fi


# 4. Test-Logins (admin, user, guest)
for TEST_USER in "${!TEST_USERS[@]}"; do
  TEST_PASS="${TEST_USERS[$TEST_USER]}"
  log "API Login-Test für $TEST_USER"
  LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$TEST_USER\", \"password\": \"$TEST_PASS\"}" 2>>"$LOGFILE")
  LOGIN_BODY=$(echo "$LOGIN" | head -n -1)
  LOGIN_CODE=$(echo "$LOGIN" | tail -n1)
  if [ "$LOGIN_CODE" = "200" ] && echo "$LOGIN_BODY" | grep -q 'access_token'; then
    log "✅ Login für $TEST_USER erfolgreich!"
  else
    log "❌ Login für $TEST_USER fehlgeschlagen! HTTP $LOGIN_CODE. Antwort: $LOGIN_BODY"
    log "[Tipp] Prüfe, ob der User existiert, das Passwort stimmt und die Datenbankverbindung im Backend funktioniert. Backend-Logs und DB-Status prüfen."
  fi
done

log "--- Liara Healthcheck abgeschlossen ---"
