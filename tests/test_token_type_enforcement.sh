#!/bin/bash
# Regression test for issue #11 (token-type enforcement): a refresh token
# must never authenticate as bearer access, and a normal access token must
# keep working. Run against a live server (see BASE_URL) - mirrors
# tests/test_auth.sh's style, no pytest/TestClient setup exists in this repo.

BASE_URL="http://localhost:8100"

echo "🧪 Liara Token-Type Enforcement Test (issue #11)"
echo "=================================================="
echo ""

echo "1️⃣  Logging in as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")
    REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['refresh_token'])")
    echo "   ✅ Login successful, got access_token + refresh_token"
else
    echo "   ❌ Login failed - cannot continue"
    exit 1
fi
echo ""

echo "2️⃣  Testing refresh token as Bearer auth on GET /auth/me (must be rejected)..."
REFRESH_AS_BEARER_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $REFRESH_TOKEN")

if [ "$REFRESH_AS_BEARER_CODE" == "401" ]; then
    echo "   ✅ Refresh token rejected as bearer auth (401 Unauthorized)"
else
    echo "   ❌ SECURITY ISSUE: refresh token accepted as bearer auth (HTTP $REFRESH_AS_BEARER_CODE)"
    exit 1
fi
echo ""

echo "3️⃣  Testing access token as Bearer auth on GET /auth/me (must still work)..."
ACCESS_AS_BEARER_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if [ "$ACCESS_AS_BEARER_CODE" == "200" ]; then
    echo "   ✅ Access token still authenticates normally (200 OK)"
else
    echo "   ❌ REGRESSION: access token no longer works (HTTP $ACCESS_AS_BEARER_CODE)"
    exit 1
fi
echo ""

echo "=================================================="
echo "✅ Token-Type Enforcement Tests Complete"
