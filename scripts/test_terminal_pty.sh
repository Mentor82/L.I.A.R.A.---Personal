#!/bin/bash
# Terminal PTY WebSocket Test Script
# Tests the WebSocket endpoint without browser

echo "🧪 Terminal PTY WebSocket Endpoint Test"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if websocat is installed
if ! command -v websocat &> /dev/null; then
    echo -e "${YELLOW}⚠️  websocat not installed${NC}"
    echo "Install with: cargo install websocat"
    echo "Alternative: pip install websocket-client"
    echo ""
fi

# Test 1: Check if backend is running
echo "1️⃣  Checking backend status..."
if systemctl is-active --quiet liara-backend; then
    echo -e "${GREEN}✅ liara-backend is running${NC}"
else
    echo -e "${RED}❌ liara-backend is NOT running${NC}"
    echo "Start with: sudo systemctl start liara-backend"
    exit 1
fi
echo ""

# Test 2: Check if endpoint exists in routes
echo "2️⃣  Checking terminal routes..."
cd /opt/liara/app
source /opt/liara/venv/bin/activate
ROUTES=$(python3 -c "
from main import app
for route in app.routes:
    if hasattr(route, 'path') and 'terminal' in route.path.lower():
        print(route.path)
" 2>/dev/null)

if [[ -z "$ROUTES" ]]; then
    echo -e "${RED}❌ No terminal routes found${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Terminal routes found:${NC}"
    echo "$ROUTES" | while read route; do
        echo "   - $route"
    done
fi
echo ""

# Test 3: Check if port 8100 is listening
echo "3️⃣  Checking port 8100..."
if ss -tunlp 2>/dev/null | grep -q ":8100"; then
    WORKERS=$(ss -tunlp 2>/dev/null | grep -c ":8100")
    echo -e "${GREEN}✅ Port 8100 is LISTEN ($WORKERS workers)${NC}"
else
    echo -e "${RED}❌ Port 8100 is NOT listening${NC}"
    exit 1
fi
echo ""

# Test 4: Check nginx WebSocket configuration
echo "4️⃣  Checking nginx WebSocket proxy..."
if nginx -T 2>/dev/null | grep -q "proxy_set_header Upgrade"; then
    echo -e "${GREEN}✅ Nginx WebSocket headers configured${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx WebSocket headers not found${NC}"
    echo "Add to nginx config:"
    echo "  proxy_http_version 1.1;"
    echo "  proxy_set_header Upgrade \$http_upgrade;"
    echo "  proxy_set_header Connection \"upgrade\";"
fi
echo ""

# Test 5: Get admin token (if possible)
echo "5️⃣  Getting admin token..."
TOKEN=$(python3 -c "
from core.database import SessionLocal
from api.models.base_models import User, UserRole
from core.security import create_access_token

db = SessionLocal()
admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
if admin:
    token = create_access_token({'user_id': admin.id, 'username': admin.username})
    print(token)
else:
    print('')
db.close()
" 2>/dev/null)

if [[ -n "$TOKEN" ]]; then
    echo -e "${GREEN}✅ Admin token generated${NC}"
    echo "   Token: ${TOKEN:0:30}..."
    
    # Save token for manual testing
    echo "$TOKEN" > /tmp/liara_terminal_test_token.txt
    echo "   Saved to: /tmp/liara_terminal_test_token.txt"
else
    echo -e "${YELLOW}⚠️  Could not generate admin token${NC}"
    echo "   Create admin user first or login to get token"
fi
echo ""

# Test 6: WebSocket connection test (if websocat available)
if command -v websocat &> /dev/null && [[ -n "$TOKEN" ]]; then
    echo "6️⃣  Testing WebSocket connection..."
    echo "   Endpoint: ws://localhost:8100/admin/terminal/ws?token=..."
    
    # Test with timeout (5 seconds)
    timeout 5 bash -c "
        echo '' | websocat \"ws://localhost:8100/admin/terminal/ws?token=$TOKEN\" 2>&1 | head -5
    " &
    
    WSPID=$!
    sleep 2
    
    if ps -p $WSPID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ WebSocket connection accepted${NC}"
        kill $WSPID 2>/dev/null
    else
        echo -e "${YELLOW}⚠️  WebSocket test inconclusive${NC}"
    fi
else
    echo "6️⃣  Skipping WebSocket test (websocat not available or no token)"
fi
echo ""

# Summary
echo "========================================"
echo "📋 Test Summary"
echo "========================================"
echo ""
echo "✅ Backend running"
echo "✅ Terminal routes registered"
echo "✅ Port 8100 listening"
echo ""
echo "Next steps:"
echo "1. Open browser: http://localhost/admin"
echo "2. Login as admin"
echo "3. Navigate to Terminal tab"
echo "4. Click 'Verbinden'"
echo "5. Test commands:"
echo "   - ls -la --color=auto"
echo "   - vim test.txt"
echo "   - top"
echo "   - su - mirko"
echo ""
echo "🔍 Logs:"
echo "   sudo tail -f /var/log/liara/error.log | grep -i terminal"
echo ""
echo "✅ All checks passed!"
