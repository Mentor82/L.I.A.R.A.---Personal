#!/bin/bash
# Regression test for issue #16 (router auth policy): ollama_router.py,
# validation_router.py, mcp_validation_router.py, and hailo_router.py were
# mounted with zero authentication - this proves the fix stays in place.
# Same bash+curl style as tests/test_auth.sh (no pytest in this repo).

BASE_URL="http://localhost:8100"

echo "🧪 Liara Router Auth Policy Test (issue #16)"
echo "=================================================="
echo ""

FAILED=0

echo "1️⃣  Logging in as admin..."
ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')
ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -z "$ADMIN_TOKEN" ]; then
    echo "   ❌ Admin login failed - cannot continue"
    exit 1
fi
echo "   ✅ Admin token acquired"
echo ""

echo "2️⃣  Registering a throwaway non-admin user..."
SUFFIX=$(date +%s)
REG_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"routertest$SUFFIX\", \"email\": \"routertest$SUFFIX@example.com\", \"password\": \"routertest12345\", \"full_name\": \"Router Test\"}")
USER_TOKEN=$(echo "$REG_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -z "$USER_TOKEN" ]; then
    echo "   ❌ Non-admin registration failed - cannot continue"
    exit 1
fi
echo "   ✅ Non-admin token acquired (routertest$SUFFIX)"
echo ""

# $1 = label, $2 = method, $3 = path, $4 = body (or "" for none)
request_status() {
    local method="$2" path="$3" body="$4" token="$5"
    local auth_header=()
    [ -n "$token" ] && auth_header=(-H "Authorization: Bearer $token")
    if [ -n "$body" ]; then
        curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$path" \
            -H "Content-Type: application/json" "${auth_header[@]}" -d "$body"
    else
        curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$path" "${auth_header[@]}"
    fi
}

echo "3️⃣  Admin-only routes must reject anonymous requests (401 or 403)..."
for route in \
    "POST|/ollama/pull|{\"model_name\": \"nonexistent-test-model\"}" \
    "DELETE|/ollama/model/nonexistent-test-model|" \
    "GET|/ollama/storage|" \
    "GET|/validate-mcp/health|" \
    "GET|/validate-mcp/tools|"
do
    IFS='|' read -r method path body <<< "$route"
    code=$(request_status "" "$method" "$path" "$body" "")
    if [ "$code" == "401" ] || [ "$code" == "403" ]; then
        echo "   ✅ $method $path anonymous -> $code"
    else
        echo "   ❌ SECURITY ISSUE: $method $path anonymous -> $code (expected 401/403)"
        FAILED=1
    fi
done
echo ""

echo "4️⃣  Admin-only routes must reject a non-admin user (403)..."
for route in \
    "POST|/ollama/pull|{\"model_name\": \"nonexistent-test-model\"}" \
    "GET|/ollama/storage|" \
    "GET|/validate-mcp/tools|"
do
    IFS='|' read -r method path body <<< "$route"
    code=$(request_status "" "$method" "$path" "$body" "$USER_TOKEN")
    if [ "$code" == "403" ]; then
        echo "   ✅ $method $path non-admin -> 403"
    else
        echo "   ❌ SECURITY ISSUE: $method $path non-admin -> $code (expected 403)"
        FAILED=1
    fi
done
echo ""

echo "5️⃣  User-level routes must reject anonymous requests, accept authenticated users..."
for route in \
    "POST|/validate/generate|{\"prompt\": \"test\"}" \
    "POST|/hailo/infer|{\"model\": \"test\", \"input\": {}}"
do
    IFS='|' read -r method path body <<< "$route"
    anon_code=$(request_status "" "$method" "$path" "$body" "")
    if [ "$anon_code" == "401" ] || [ "$anon_code" == "403" ]; then
        echo "   ✅ $method $path anonymous -> $anon_code"
    else
        echo "   ❌ SECURITY ISSUE: $method $path anonymous -> $anon_code (expected 401/403)"
        FAILED=1
    fi
    user_code=$(request_status "" "$method" "$path" "$body" "$USER_TOKEN")
    if [ "$user_code" == "401" ] || [ "$user_code" == "403" ]; then
        echo "   ❌ REGRESSION: $method $path authenticated non-admin -> $user_code (should pass auth, even if the route then fails for other reasons)"
        FAILED=1
    else
        echo "   ✅ $method $path authenticated non-admin -> $user_code (passed auth layer)"
    fi
done
echo ""

echo "6️⃣  Deliberately public routes must stay public (200, no token needed)..."
for path in "/ollama/available" "/ollama/library/search?query=llama"; do
    code=$(request_status "" "GET" "$path" "" "")
    if [ "$code" == "200" ]; then
        echo "   ✅ GET $path anonymous -> 200 (still public)"
    else
        echo "   ❌ REGRESSION: GET $path anonymous -> $code (expected 200, was this meant to stay public?)"
        FAILED=1
    fi
done
echo ""

echo "=================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "✅ Router Auth Policy Tests Complete"
else
    echo "❌ One or more checks failed"
    exit 1
fi
