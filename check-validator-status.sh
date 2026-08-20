#!/bin/bash
# AI-VALIDATOR SYSTEM STATUS CHECK
# Script zum Prüfen des AI-Validator Integrations-Status
# Usage: bash /opt/liara/check-validator-status.sh

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         AI-VALIDATOR INTEGRATION STATUS CHECK                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Liara Backend läuft
echo -n "1️⃣  Liara Backend Service... "
if sudo systemctl is-active --quiet liara-backend; then
    echo -e "${GREEN}✅ AKTIV${NC}"
else
    echo -e "${RED}❌ INAKTIV${NC}"
fi

# Test 2: Liara Backend erreichbar
echo -n "2️⃣  Liara Backend HTTP... "
if curl -s -f http://localhost:8100/ > /dev/null; then
    echo -e "${GREEN}✅ ERREICHBAR${NC}"
else
    echo -e "${RED}❌ NICHT ERREICHBAR${NC}"
fi

# Test 3: AI-Validator Health
echo -n "3️⃣  AI-Validator Health... "
if curl -s -f http://192.168.178.150:5000/health > /dev/null; then
    echo -e "${GREEN}✅ ERREICHBAR${NC}"
else
    echo -e "${RED}❌ NICHT ERREICHBAR${NC}"
fi

# Test 4: Validation Endpoint
echo -n "4️⃣  Validation Endpoint... "
if curl -s -f http://localhost:8100/validate/health > /dev/null; then
    echo -e "${GREEN}✅ FUNKTIONIERT${NC}"
else
    echo -e "${RED}❌ FUNKTIONIERT NICHT${NC}"
fi

# Test 5: Python Validation Test
echo -n "5️⃣  Python Validation Test... "
RESPONSE=$(curl -s -X POST http://localhost:8100/validate/python \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"test\")", "strict": false}' 2>/dev/null)

if echo "$RESPONSE" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ FUNKTIONIERT${NC}"
else
    echo -e "${RED}❌ FEHLER${NC}"
fi

# Test 6: Error Detection Test
echo -n "6️⃣  Error Detection Test... "
RESPONSE=$(curl -s -X POST http://localhost:8100/validate/python \
  -H "Content-Type: application/json" \
  -d '{"code": "def broken(", "strict": false}' 2>/dev/null)

if echo "$RESPONSE" | grep -q '"status":"error"'; then
    echo -e "${GREEN}✅ FUNKTIONIERT${NC}"
else
    echo -e "${RED}❌ FUNKTIONIERT NICHT${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                       ENDPOINT STATUS                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get health status
echo "📊 Liara Validation Health:"
curl -s http://localhost:8100/validate/health | python3 -m json.tool 2>/dev/null || echo "❌ Fehler beim Abrufen"

echo ""
echo "🔧 AI-Validator Endpoints verfügbar:"
echo "  • POST /validate/code           - Allgemeine Validierung"
echo "  • POST /validate/python         - Python Validierung"
echo "  • POST /validate/javascript     - JavaScript Validierung"
echo "  • POST /validate/typescript     - TypeScript Validierung"
echo "  • POST /validate/bash           - Bash/Shell Validierung"
echo "  • POST /validate/c              - C Code Validierung"
echo "  • POST /validate/cpp            - C++ Code Validierung"
echo "  • POST /validate/go             - Go Code Validierung"
echo "  • POST /validate/rust           - Rust Code Validierung"
echo "  • POST /validate/php            - PHP Code Validierung"
echo "  • POST /validate/ruby           - Ruby Code Validierung"
echo "  • POST /validate/java           - Java Code Validierung"
echo "  • POST /validate/sql            - SQL Code Validierung"
echo "  • POST /validate/html           - HTML Code Validierung"
echo "  • POST /validate/css            - CSS Code Validierung"
echo "  • POST /validate/json           - JSON Validierung"
echo "  • POST /validate/yaml           - YAML Validierung"
echo "  • GET  /validate/health         - Health Check"

echo ""
echo "📚 Dokumentation:"
echo "  • /opt/liara/AI-VALIDATOR-INTEGRATION.md     - Main Documentation"
echo "  • /opt/liara/EXTENDED-LANGUAGE-SUPPORT.md    - Language Support Details"
echo ""
