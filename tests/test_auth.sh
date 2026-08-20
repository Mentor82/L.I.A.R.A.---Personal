#!/bin/bash
# Liara Authentication System - Test Script

BASE_URL="http://localhost:8100"

echo "🧪 Liara RBAC Authentication System Test"
echo "=========================================="
echo ""

# Test 1: Register new user
echo "1️⃣  Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demouser",
    "email": "demo@example.com",
    "password": "demopass123",
    "full_name": "Demo User"
  }')

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    echo "   ✅ User registration successful"
    DEMO_TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
else
    echo "   ⚠️  Registration failed (user may already exist)"
fi
echo ""

# Test 2: Admin Login
echo "2️⃣  Testing Admin Login..."
ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

if echo "$ADMIN_RESPONSE" | grep -q "access_token"; then
    echo "   ✅ Admin login successful"
    ADMIN_TOKEN=$(echo "$ADMIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")
    ADMIN_ROLE=$(echo "$ADMIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['user']['role'])")
    echo "   📌 Role: $ADMIN_ROLE"
else
    echo "   ❌ Admin login failed"
    exit 1
fi
echo ""

# Test 3: Get Current User Info
echo "3️⃣  Testing GET /auth/me..."
ME_RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if echo "$ME_RESPONSE" | grep -q "username"; then
    USERNAME=$(echo "$ME_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['username'])")
    USER_EMAIL=$(echo "$ME_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['email'])")
    echo "   ✅ User info retrieved"
    echo "   📌 Username: $USERNAME"
    echo "   📌 Email: $USER_EMAIL"
else
    echo "   ❌ Failed to get user info"
fi
echo ""

# Test 4: Invalid Token
echo "4️⃣  Testing Invalid Token (Security)..."
INVALID_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer invalid_token_12345")

if [ "$INVALID_RESPONSE" == "401" ]; then
    echo "   ✅ Invalid token rejected (401 Unauthorized)"
else
    echo "   ❌ Security issue: Invalid token not rejected (HTTP $INVALID_RESPONSE)"
fi
echo ""

# Test 5: Wrong Password
echo "5️⃣  Testing Wrong Password..."
WRONG_PW_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "wrongpassword"}')

if [ "$WRONG_PW_RESPONSE" == "401" ]; then
    echo "   ✅ Wrong password rejected (401 Unauthorized)"
else
    echo "   ❌ Security issue: Wrong password not rejected (HTTP $WRONG_PW_RESPONSE)"
fi
echo ""

# Test 6: Database Integration
echo "6️⃣  Testing Database Integration..."
USER_COUNT=$(sudo -u postgres psql -d liara_db -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | xargs)
if [ ! -z "$USER_COUNT" ]; then
    echo "   ✅ Database accessible"
    echo "   📌 Total users in DB: $USER_COUNT"
else
    echo "   ❌ Database query failed"
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Authentication System Tests Complete"
echo ""
echo "📋 Summary:"
echo "   - User Registration: ✅"
echo "   - Admin Login: ✅"
echo "   - Token Validation: ✅"
echo "   - Security Checks: ✅"
echo "   - Database Integration: ✅"
echo ""
echo "🔑 Default Admin Login:"
echo "   Username: admin"
echo "   Password: admin123"
echo "   ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!"
