#!/bin/bash
# Liara System Health Check
# Prüft alle Services und zeigt detaillierten Status

echo "🌙 Liara System Health Check"
echo "============================"
echo ""

# 1. Backend Service Status
echo "📡 Backend Service:"
if systemctl is-active --quiet liara-backend; then
    echo "  ✅ liara-backend.service is running"
    BACKEND_PID=$(systemctl show -p MainPID --value liara-backend)
    BACKEND_MEM=$(ps -p $BACKEND_PID -o rss= 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
    echo "  PID: $BACKEND_PID | Memory: $BACKEND_MEM"
else
    echo "  ❌ liara-backend.service is NOT running"
fi
echo ""

# 2. Backend API Health
echo "🔌 Backend API:"
HEALTH=$(curl -s http://localhost:8100/health/full 2>&1)
if [ $? -eq 0 ]; then
    echo "  ✅ API responding on port 8100"
    echo "$HEALTH" | grep -q '"api":"ok"' && echo "  ✅ API status: OK"
    echo "$HEALTH" | grep -q '"ollama":"ok"' && echo "  ✅ Ollama: Connected" || echo "  ⚠️  Ollama: Not connected"
    
    # Extract metrics
    RAM_PERCENT=$(echo "$HEALTH" | grep -o '"percent":[0-9.]*' | head -1 | cut -d: -f2)
    DISK_PERCENT=$(echo "$HEALTH" | grep -o '"percent":[0-9.]*' | tail -1 | cut -d: -f2)
    [ ! -z "$RAM_PERCENT" ] && echo "  📊 RAM: ${RAM_PERCENT}%"
    [ ! -z "$DISK_PERCENT" ] && echo "  💾 Disk: ${DISK_PERCENT}%"
else
    echo "  ❌ API not responding"
fi
echo ""

# 3. Ollama Service
echo "🤖 Ollama Service:"
if systemctl is-active --quiet ollama; then
    echo "  ✅ ollama.service is running"
    MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | wc -l)
    [ $MODELS -gt 0 ] && echo "  📦 Models loaded: $MODELS"
else
    echo "  ❌ ollama.service is NOT running"
fi
echo ""

# 4. Frontend Service
echo "🎨 Frontend Service:"
if systemctl is-active --quiet liara-frontend; then
    echo "  ✅ liara-frontend.service is running"
else
    echo "  ⚠️  liara-frontend.service is NOT running (may be manual)"
fi
echo ""

# 5. PostgreSQL Database
echo "🗄️  PostgreSQL Database:"
if systemctl is-active --quiet postgresql; then
    echo "  ✅ postgresql.service is running"
    # Test connection
    if sudo -u postgres psql -d liara_db -c "SELECT 1;" &>/dev/null; then
        echo "  ✅ Database 'liara_db' accessible"
        
        # Count records
        NOTES=$(sudo -u postgres psql -d liara_db -tAc "SELECT COUNT(*) FROM notes;" 2>/dev/null)
        TASKS=$(sudo -u postgres psql -d liara_db -tAc "SELECT COUNT(*) FROM tasks;" 2>/dev/null)
        EVENTS=$(sudo -u postgres psql -d liara_db -tAc "SELECT COUNT(*) FROM calendar_events;" 2>/dev/null)
        MEMORY=$(sudo -u postgres psql -d liara_db -tAc "SELECT COUNT(*) FROM semantic_metadata;" 2>/dev/null)
        
        [ ! -z "$NOTES" ] && echo "  📝 Notes: $NOTES"
        [ ! -z "$TASKS" ] && echo "  ✅ Tasks: $TASKS"
        [ ! -z "$EVENTS" ] && echo "  📅 Events: $EVENTS"
        [ ! -z "$MEMORY" ] && echo "  🧠 4D Memory Entries: $MEMORY"
    else
        echo "  ❌ Cannot connect to database"
    fi
else
    echo "  ❌ postgresql.service is NOT running"
fi
echo ""

# 6. Redis Service
echo "🔴 Redis Service:"
if systemctl is-active --quiet redis-server; then
    echo "  ✅ redis-server.service is running"
    if redis-cli ping &>/dev/null; then
        echo "  ✅ Redis responding to PING"
    else
        echo "  ⚠️  Redis not responding"
    fi
else
    echo "  ⚠️  redis-server.service is NOT running"
fi
echo ""

# 7. Neo4j Service (if installed)
echo "🕸️  Neo4j Service:"
if systemctl list-units --full --all | grep -q neo4j; then
    if systemctl is-active --quiet neo4j; then
        echo "  ✅ neo4j.service is running"
    else
        echo "  ❌ neo4j.service is NOT running"
    fi
else
    echo "  ℹ️  Neo4j not installed or not managed by systemd"
fi
echo ""

# 8. Nginx
echo "🌐 Nginx:"
if systemctl is-active --quiet nginx; then
    echo "  ✅ nginx.service is running"
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q 200; then
        echo "  ✅ Nginx responding on port 80"
    fi
else
    echo "  ❌ nginx.service is NOT running"
fi
echo ""

# 9. System Resources
echo "💻 System Resources:"
LOAD=$(uptime | awk -F'load average:' '{print $2}' | xargs)
UPTIME=$(uptime -p)
echo "  ⏱️  Uptime: $UPTIME"
echo "  📊 Load Average: $LOAD"

# Memory
MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
MEM_USED=$(free -h | awk '/^Mem:/ {print $3}')
MEM_PERCENT=$(free | awk '/^Mem:/ {printf "%.1f", $3/$2*100}')
echo "  🧠 Memory: $MEM_USED / $MEM_TOTAL ($MEM_PERCENT%)"

# Disk
DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
DISK_USED=$(df -h / | awk 'NR==2 {print $3}')
DISK_PERCENT=$(df / | awk 'NR==2 {print $5}')
echo "  💾 Disk: $DISK_USED / $DISK_TOTAL ($DISK_PERCENT)"

echo ""
echo "============================"

# Overall Status
ERRORS=0
systemctl is-active --quiet liara-backend || ((ERRORS++))
systemctl is-active --quiet postgresql || ((ERRORS++))
curl -s http://localhost:8100/ &>/dev/null || ((ERRORS++))

if [ $ERRORS -eq 0 ]; then
    echo "✅ Overall Status: HEALTHY"
else
    echo "⚠️  Overall Status: $ERRORS critical service(s) down"
fi
