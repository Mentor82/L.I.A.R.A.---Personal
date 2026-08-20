#!/bin/bash

################################################################################
# Liara Comprehensive Health Check Script
# Version: 2.0
# Date: 2025-12-04
#
# Überprüft:
# - System-Ressourcen (CPU, RAM, Disk, Network)
# - Services (Backend, Frontend, Nginx, PostgreSQL, Ollama)
# - API-Endpoints (Health, Auth, Core-Features)
# - Database-Connectivity
# - Security & Performance-Metriken
################################################################################

set +e  # Exit on error, undefined vars, pipe failures

# ============================================================================
# KONFIGURATION
# ============================================================================

LOGFILE="/opt/liara/liara_healthcheck.log"
API_URL="http://localhost:8100"
FRONTEND_URL="http://localhost:5173"
NGINX_URL="http://localhost"

# Test-Credentials
declare -A TEST_USERS=(
  [admin]="admin123"
  [user]="user123"
  [guest]="guest123"
)

# Service-Namen
SERVICES=(
  "liara-backend"
  "liara-frontend"
  "nginx"
  "postgresql"
  "ollama"
)

# API-Endpoints zum Testen
declare -A API_ENDPOINTS=(
  [health]="/"
  [system_info]="/info"
  [dashboard]="/dashboard/info"
  [mood_status]="/mood/status"
  [sentiment_categories]="/sentiment/categories"
  [memory_status]="/memory/status"
)

# Farben für Terminal-Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Statistiken
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# ============================================================================
# HELPER-FUNKTIONEN
# ============================================================================

log() {
  local level="$1"
  shift
  local message="$*"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  case "$level" in
    INFO)
      echo -e "${CYAN}[INFO]${NC} $message" | tee -a "$LOGFILE"
      ;;
    SUCCESS)
      echo -e "${GREEN}[✓]${NC} $message" | tee -a "$LOGFILE"
      ((PASSED_CHECKS++))
      ;;
    WARNING)
      echo -e "${YELLOW}[⚠]${NC} $message" | tee -a "$LOGFILE"
      ((WARNING_CHECKS++))
      ;;
    ERROR)
      echo -e "${RED}[✗]${NC} $message" | tee -a "$LOGFILE"
      ((FAILED_CHECKS++))
      ;;
    HEADER)
      echo -e "\n${PURPLE}═══════════════════════════════════════════════════${NC}" | tee -a "$LOGFILE"
      echo -e "${PURPLE}  $message${NC}" | tee -a "$LOGFILE"
      echo -e "${PURPLE}═══════════════════════════════════════════════════${NC}\n" | tee -a "$LOGFILE"
      ;;
  esac
  
  echo "[$timestamp] [$level] $message" >> "$LOGFILE"
  ((TOTAL_CHECKS++))
}

header() {
  log HEADER "$1"
}

# HTTP-Request mit Timeout und Error-Handling
http_check() {
  local url="$1"
  local expected_code="${2:-200}"
  local timeout="${3:-5}"
  
  local response=$(curl -s -w "\n%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo -e "\n000")
  local body=$(echo "$response" | head -n -1)
  local code=$(echo "$response" | tail -n1)
  
  echo "$code|$body"
}

# Service-Status-Check
check_service() {
  local service="$1"
  
  if systemctl is-active --quiet "$service"; then
    log SUCCESS "Service '$service' läuft"
    
    # Uptime
    local uptime=$(systemctl show "$service" --property=ActiveEnterTimestamp --value)
    if [ -n "$uptime" ]; then
      log INFO "  └─ Gestartet: $uptime"
    fi
    
    return 0
  else
    log ERROR "Service '$service' läuft NICHT"
    
    # Zeige letzten Fehler
    local last_error=$(systemctl status "$service" --no-pager -n 5 2>/dev/null | grep -i "error" | head -1)
    if [ -n "$last_error" ]; then
      log ERROR "  └─ Letzter Fehler: $last_error"
    fi
    
    return 1
  fi
}

# Port-Check
check_port() {
  local port="$1"
  local service_name="$2"
  
  if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    local process=$(lsof -i ":$port" -sTCP:LISTEN | tail -n 1 | awk '{print $1 " (PID: " $2 ")"}')
    log SUCCESS "Port $port offen: $service_name [$process]"
    return 0
  else
    log ERROR "Port $port NICHT offen: $service_name"
    return 1
  fi
}

# ============================================================================
# HEALTH-CHECK FUNKTIONEN
# ============================================================================

check_system_resources() {
  header "SYSTEM-RESSOURCEN"
  
  # CPU
  local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
  local cpu_cores=$(nproc)
  log INFO "CPU Load: $cpu_load (Cores: $cpu_cores)"
  
  # RAM
  local mem_total=$(free -h | awk '/^Mem:/ {print $2}')
  local mem_used=$(free -h | awk '/^Mem:/ {print $3}')
  local mem_percent=$(free | awk '/^Mem:/ {printf "%.0f", $3/$2 * 100}')
  
  log INFO "RAM: $mem_used / $mem_total (${mem_percent}%)"
  
  if [ "$mem_percent" -gt 90 ]; then
    log WARNING "RAM-Auslastung kritisch hoch: ${mem_percent}%"
  elif [ "$mem_percent" -gt 75 ]; then
    log WARNING "RAM-Auslastung hoch: ${mem_percent}%"
  else
    log SUCCESS "RAM-Auslastung normal: ${mem_percent}%"
  fi
  
  # Disk
  local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
  local disk_used=$(df -h / | awk 'NR==2 {print $3}')
  local disk_total=$(df -h / | awk 'NR==2 {print $2}')
  
  log INFO "Disk: $disk_used / $disk_total (${disk_usage}%)"
  
  if [ "$disk_usage" -gt 90 ]; then
    log ERROR "Disk-Auslastung kritisch: ${disk_usage}%"
  elif [ "$disk_usage" -gt 75 ]; then
    log WARNING "Disk-Auslastung hoch: ${disk_usage}%"
  else
    log SUCCESS "Disk-Auslastung normal: ${disk_usage}%"
  fi
  
  # Uptime
  local uptime_info=$(uptime -p)
  log INFO "System Uptime: $uptime_info"
}

check_services() {
  header "SERVICE-STATUS"
  
  for service in "${SERVICES[@]}"; do
    check_service "$service"
  done
}

check_ports() {
  header "PORT-VERFÜGBARKEIT"
  
  check_port 8100 "Backend (Gunicorn/Uvicorn)"
  check_port 5173 "Frontend (Vite)"
  check_port 80 "Nginx (HTTP)"
  check_port 443 "Nginx (HTTPS)"
  check_port 5432 "PostgreSQL"
  check_port 11434 "Ollama"
}

check_database() {
  header "DATABASE-CONNECTIVITY"
  
  # PostgreSQL-Version
  local pg_version=$(psql --version | awk '{print $3}')
  log INFO "PostgreSQL Version: $pg_version"
  
  # Verbindungstest
  if PGPASSWORD="liaras_own" psql -U liara -h localhost -d liara_db -c "SELECT version();" >/dev/null 2>&1; then
    log SUCCESS "Datenbankverbindung erfolgreich"
    
    # Tabellen-Count
    local table_count=$(PGPASSWORD="liaras_own" psql -U liara -h localhost -d liara_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
    log INFO "  └─ Tabellen: $table_count"
    
    # Datenbankgröße
    local db_size=$(PGPASSWORD="liaras_own" psql -U liara -h localhost -d liara_db -t -c "SELECT pg_size_pretty(pg_database_size('liara_db'));" 2>/dev/null | tr -d ' ')
    log INFO "  └─ Größe: $db_size"
    
    # User-Count
    local user_count=$(PGPASSWORD="liaras_own" psql -U liara -h localhost -d liara_db -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    log INFO "  └─ Users: $user_count"
    
  else
    log ERROR "Datenbankverbindung fehlgeschlagen"
    log ERROR "  └─ Prüfe Credentials, PostgreSQL-Status und pg_hba.conf"
  fi
}

check_api_endpoints() {
  header "API-ENDPOINTS"
  
  for endpoint_name in "${!API_ENDPOINTS[@]}"; do
    local endpoint="${API_ENDPOINTS[$endpoint_name]}"
    local url="$API_URL$endpoint"
    
    local result=$(http_check "$url")
    local code=$(echo "$result" | cut -d'|' -f1)
    local body=$(echo "$result" | cut -d'|' -f2-)
    
    if [ "$code" = "200" ]; then
      log SUCCESS "Endpoint '$endpoint_name' ($endpoint): HTTP $code"
      
      # Zeige kurze Response-Info
      if command -v jq >/dev/null 2>&1 && echo "$body" | jq -e . >/dev/null 2>&1; then
        local preview=$(echo "$body" | jq -c '.' | head -c 100)
        log INFO "  └─ Response: $preview..."
      fi
    elif [ "$code" = "000" ]; then
      log ERROR "Endpoint '$endpoint_name' ($endpoint): TIMEOUT/UNREACHABLE"
    else
      log WARNING "Endpoint '$endpoint_name' ($endpoint): HTTP $code"
    fi
  done
}

check_authentication() {
  header "AUTHENTICATION"
  
  for username in "${!TEST_USERS[@]}"; do
    local password="${TEST_USERS[$username]}"
    
    local result=$(curl -s -w "\n%{http_code}" --max-time 5 \
      -X POST "$API_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\": \"$username\", \"password\": \"$password\"}" \
      2>/dev/null || echo -e "\n000")
    
    local body=$(echo "$result" | head -n -1)
    local code=$(echo "$result" | tail -n1)
    
    if [ "$code" = "200" ] && echo "$body" | grep -q "access_token"; then
      log SUCCESS "Login für '$username' erfolgreich"
      
      # Token-Extraktion (wenn jq verfügbar)
      if command -v jq >/dev/null 2>&1; then
        local token=$(echo "$body" | jq -r '.access_token' 2>/dev/null)
        if [ -n "$token" ] && [ "$token" != "null" ]; then
          log INFO "  └─ Token: ${token:0:20}..."
        fi
      fi
    elif [ "$code" = "000" ]; then
      log ERROR "Login für '$username': TIMEOUT"
    else
      log ERROR "Login für '$username' fehlgeschlagen: HTTP $code"
    fi
  done
}

check_ollama() {
  header "OLLAMA AI-MODELS"
  
  # Ollama-Verfügbarkeit
  local result=$(http_check "http://localhost:11434/api/tags")
  local code=$(echo "$result" | cut -d'|' -f1)
  local body=$(echo "$result" | cut -d'|' -f2-)
  
  if [ "$code" = "200" ]; then
    log SUCCESS "Ollama API erreichbar"
    
    # Model-Liste (wenn jq verfügbar)
    if command -v jq >/dev/null 2>&1 && echo "$body" | jq -e . >/dev/null 2>&1; then
      local models=$(echo "$body" | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
      if [ -n "$models" ]; then
        log INFO "  └─ Verfügbare Models: $models"
      fi
    fi
  else
    log WARNING "Ollama API nicht erreichbar: HTTP $code"
    log INFO "  └─ Prüfe: systemctl status ollama"
  fi
}

check_nginx() {
  header "NGINX-KONFIGURATION"
  
  # Config-Test
  if nginx -t >/dev/null 2>&1; then
    log SUCCESS "Nginx-Konfiguration valide"
  else
    log ERROR "Nginx-Konfiguration fehlerhaft"
    nginx -t 2>&1 | tee -a "$LOGFILE"
  fi
  
  # Proxy-Test (API via Nginx)
  local result=$(http_check "$NGINX_URL/api/")
  local code=$(echo "$result" | cut -d'|' -f1)
  
  if [ "$code" = "200" ]; then
    log SUCCESS "Nginx Proxy (API) funktioniert"
  else
    log WARNING "Nginx Proxy (API) Probleme: HTTP $code"
  fi
}

check_security() {
  header "SECURITY-CHECKS"
  
  # Firewall
  if command -v ufw >/dev/null 2>&1; then
    if ufw status | grep -q "Status: active"; then
      log SUCCESS "UFW Firewall aktiv"
      
      # Offene Ports
      local open_ports=$(ufw status | grep ALLOW | wc -l)
      log INFO "  └─ Erlaubte Verbindungen: $open_ports"
    else
      log WARNING "UFW Firewall nicht aktiv"
    fi
  fi
  
  # SSL-Zertifikate
  if [ -d "/etc/letsencrypt/live" ]; then
    local cert_count=$(find /etc/letsencrypt/live -name "cert.pem" 2>/dev/null | wc -l)
    log INFO "SSL-Zertifikate gefunden: $cert_count"
    
    # Ablaufdatum prüfen (wenn openssl verfügbar)
    if command -v openssl >/dev/null 2>&1; then
      for cert in /etc/letsencrypt/live/*/cert.pem; do
        if [ -f "$cert" ]; then
          local domain=$(dirname "$cert" | xargs basename)
          local expiry=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2)
          log INFO "  └─ $domain: Läuft ab am $expiry"
        fi
      done
    fi
  fi
}

check_performance() {
  header "PERFORMANCE-METRIKEN"
  
  # Backend-Response-Zeit
  local start=$(date +%s%N)
  local result=$(http_check "$API_URL/")
  local end=$(date +%s%N)
  local duration=$(( (end - start) / 1000000 ))
  
  log INFO "Backend Response-Zeit: ${duration}ms"
  
  if [ "$duration" -lt 100 ]; then
    log SUCCESS "Backend sehr schnell (<100ms)"
  elif [ "$duration" -lt 500 ]; then
    log SUCCESS "Backend schnell (<500ms)"
  elif [ "$duration" -lt 1000 ]; then
    log WARNING "Backend langsam (${duration}ms)"
  else
    log ERROR "Backend sehr langsam (${duration}ms)"
  fi
  
  # Worker-Count (Gunicorn)
  local worker_count=$(pgrep -f "gunicorn.*worker" | wc -l)
  log INFO "Gunicorn Workers: $worker_count"
}

# ============================================================================
# SUMMARY
# ============================================================================

print_summary() {
  header "ZUSAMMENFASSUNG"
  
  local total=$((PASSED_CHECKS + FAILED_CHECKS + WARNING_CHECKS))
  local success_rate=0
  
  if [ "$total" -gt 0 ]; then
    success_rate=$(awk "BEGIN {printf \"%.1f\", ($PASSED_CHECKS / $total) * 100}")
  fi
  
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOGFILE"
  echo -e "${GREEN}  ✓ Erfolgreich:  $PASSED_CHECKS${NC}" | tee -a "$LOGFILE"
  echo -e "${YELLOW}  ⚠ Warnungen:    $WARNING_CHECKS${NC}" | tee -a "$LOGFILE"
  echo -e "${RED}  ✗ Fehler:       $FAILED_CHECKS${NC}" | tee -a "$LOGFILE"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOGFILE"
  echo -e "${PURPLE}  Erfolgsrate: $success_rate%${NC}" | tee -a "$LOGFILE"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOGFILE"
  
  if [ "$FAILED_CHECKS" -eq 0 ]; then
    echo -e "\n${GREEN}🎉 System ist gesund!${NC}\n" | tee -a "$LOGFILE"
  elif [ "$FAILED_CHECKS" -lt 3 ]; then
    echo -e "\n${YELLOW}⚠️  System läuft mit kleineren Problemen${NC}\n" | tee -a "$LOGFILE"
  else
    echo -e "\n${RED}❌ System hat kritische Probleme!${NC}\n" | tee -a "$LOGFILE"
  fi
  
  echo -e "Logfile: ${BLUE}$LOGFILE${NC}\n" | tee -a "$LOGFILE"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
  # Logfile vorbereiten
  : > "$LOGFILE"  # Truncate
  
  # Banner
  echo -e "${PURPLE}" | tee -a "$LOGFILE"
  echo "  ╔═══════════════════════════════════════════════════╗" | tee -a "$LOGFILE"
  echo "  ║                                                   ║" | tee -a "$LOGFILE"
  echo "  ║        🌙 LIARA HEALTH CHECK v2.0 🌙             ║" | tee -a "$LOGFILE"
  echo "  ║                                                   ║" | tee -a "$LOGFILE"
  echo "  ║        $(date '+%Y-%m-%d %H:%M:%S')                      ║" | tee -a "$LOGFILE"
  echo "  ║                                                   ║" | tee -a "$LOGFILE"
  echo "  ╚═══════════════════════════════════════════════════╝" | tee -a "$LOGFILE"
  echo -e "${NC}\n" | tee -a "$LOGFILE"
  
  # Checks ausführen
  check_system_resources
  check_services
  check_ports
  check_database
  check_api_endpoints
  check_authentication
  check_ollama
  check_nginx
  check_security
  check_performance
  
  # Summary
  print_summary
}

# Script ausführen
main "$@"
