#!/bin/bash
# Frontend Authentication Integration Test
# Tests the complete auth flow: login, token storage, API calls with Bearer token

BASE_URL="http://localhost:8100"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Frontend Authentication Integration Test"
echo "========================================="
echo ""

# Test 1: Login and get token
echo "Test 1: Login as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))")
USERNAME=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('user', {}).get('username', ''))")

if [ ! -z "$TOKEN" ] && [ "$USERNAME" == "admin" ]; then
    echo -e "${GREEN}✓ Login successful - Token received${NC}"
    echo "  Username: $USERNAME"
else
    echo -e "${RED}✗ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo ""

# Test 2: Access protected endpoint with token
echo "Test 2: Access /auth/me with Bearer token..."
ME_RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN")

ME_USERNAME=$(echo "$ME_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('username', ''))")

if [ "$ME_USERNAME" == "admin" ]; then
    echo -e "${GREEN}✓ Token validation successful${NC}"
    echo "  User: $ME_USERNAME"
else
    echo -e "${RED}✗ Token validation failed${NC}"
    echo "$ME_RESPONSE"
    exit 1
fi

echo ""

# Test 3: Access protected endpoint without token (should fail)
echo "Test 3: Access /auth/me without token (should fail)..."
NO_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/auth/me")
HTTP_CODE=$(echo "$NO_TOKEN_RESPONSE" | tail -1)

if [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}✓ Correctly rejected unauthenticated request${NC}"
    echo "  HTTP Status: 401"
else
    echo -e "${RED}✗ Should have returned 401 Unauthorized${NC}"
    echo "$NO_TOKEN_RESPONSE"
fi

echo ""

# Test 4: Access chat endpoint with token
echo "Test 4: Access /chat/models with Bearer token..."
MODELS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/chat/models" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$MODELS_RESPONSE" | tail -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Chat endpoint accessible with token${NC}"
    echo "  HTTP Status: 200"
else
    echo -e "${YELLOW}⚠ Chat endpoint returned $HTTP_CODE (may need backend restart)${NC}"
fi

echo ""

# Test 5: Access tasks endpoint with token
echo "Test 5: Access /tasks with Bearer token..."
TASKS_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/tasks/" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$TASKS_RESPONSE" | tail -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Tasks endpoint accessible with token${NC}"
    echo "  HTTP Status: 200"
else
    echo -e "${RED}✗ Tasks endpoint returned $HTTP_CODE${NC}"
    echo "$(echo "$TASKS_RESPONSE" | head -n -1)"
fi

echo ""

# Test 6: Access calendar endpoint with token
echo "Test 6: Access /calendar with Bearer token..."
CALENDAR_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/calendar/" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$CALENDAR_RESPONSE" | tail -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Calendar endpoint accessible with token${NC}"
    echo "  HTTP Status: 200"
else
    echo -e "${RED}✗ Calendar endpoint returned $HTTP_CODE${NC}"
fi

echo ""

# Test 7: Test Mirko-specific user
echo "Test 7: Login as Mirko (if exists)..."
MIRKO_LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"mirko","password":"mirko123"}' 2>/dev/null)

MIRKO_TOKEN=$(echo "$MIRKO_LOGIN" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ ! -z "$MIRKO_TOKEN" ]; then
    echo -e "${GREEN}✓ Mirko user exists and can login${NC}"
    echo -e "${YELLOW}  Note: Mirko should receive personalized greeting in chat${NC}"
else
    echo -e "${YELLOW}⚠ Mirko user not found (create with: username=mirko, password=mirko123)${NC}"
fi

echo ""
echo "========================================="
echo "Frontend Auth Test Complete"
echo "========================================="
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Restart backend: sudo systemctl restart liara (or kill + restart uvicorn)"
echo "2. Start frontend: cd /opt/liara/frontend && npm run dev"
echo "3. Open browser: http://localhost:5173"
echo "4. Login with: admin / admin123"
echo "5. Check console for 'Hi Mirko!' or generic greeting"
echo ""
