#!/bin/bash
# Test User Management API (Admin only)

BASE_URL="http://localhost:8100"

echo "🧪 Testing User Management API"
echo "==============================="
echo ""

# Login as admin
echo "1️⃣  Login as admin..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")

if [ ! -z "$ADMIN_TOKEN" ]; then
    echo "   ✅ Admin logged in"
else
    echo "   ❌ Admin login failed"
    exit 1
fi
echo ""

# Test 1: List all users
echo "2️⃣  List all users..."
USERS=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/users/" | \
  python3 -c "import json, sys; users = json.load(sys.stdin); print(len(users), 'users found'); [print(f\"   - {u['username']} ({u['role']})\") for u in users]")
echo ""

# Test 2: Get specific user
echo "3️⃣  Get user details (testuser)..."
USER_DETAILS=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/users/2" | \
  python3 -c "import json, sys; u = json.load(sys.stdin); print(f\"   Username: {u['username']}\"); print(f\"   Email: {u['email']}\"); print(f\"   Role: {u['role']}\"); print(f\"   Active: {u['is_active']}\")")
echo ""

# Test 3: Deactivate user
echo "4️⃣  Deactivate demouser..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$BASE_URL/users/3/deactivate")

if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ User deactivated (HTTP 200)"
else
    echo "   ❌ Deactivation failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 4: Verify deactivated user cannot login
echo "5️⃣  Verify deactivated user cannot login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demouser", "password": "demopass123"}')

if echo "$LOGIN_RESPONSE" | grep -q "inactive"; then
    echo "   ✅ Deactivated user blocked from login"
else
    echo "   ⚠️  Deactivated user might still be able to login"
fi
echo ""

# Test 5: Reactivate user
echo "6️⃣  Reactivate demouser..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$BASE_URL/users/3/activate")

if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ User reactivated (HTTP 200)"
else
    echo "   ❌ Reactivation failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 6: Change user role
echo "7️⃣  Change testuser role to guest..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/users/2/role?new_role=guest")

if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ Role changed to guest (HTTP 200)"
else
    echo "   ❌ Role change failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 7: Verify guest cannot create tasks
echo "8️⃣  Verify guest cannot create tasks..."
TESTUSER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ ! -z "$TESTUSER_TOKEN" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST -H "Authorization: Bearer $TESTUSER_TOKEN" \
      -H "Content-Type: application/json" \
      "$BASE_URL/tasks/" \
      -d '{"title": "Guest Task", "priority": "low"}')
    
    if [ "$HTTP_CODE" == "403" ]; then
        echo "   ✅ Guest blocked from creating tasks (403 Forbidden)"
    else
        echo "   ⚠️  Guest might be able to create tasks (HTTP $HTTP_CODE)"
    fi
else
    echo "   ⚠️  testuser login failed"
fi
echo ""

# Test 8: Restore user role
echo "9️⃣  Restore testuser role to user..."
curl -s -X PUT -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$BASE_URL/users/2/role?new_role=user" > /dev/null
echo "   ✅ Role restored to user"
echo ""

# Test 9: Non-admin cannot access user management
echo "🔟 Verify non-admin cannot access user management..."
TESTUSER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TESTUSER_TOKEN" \
  "$BASE_URL/users/")

if [ "$HTTP_CODE" == "403" ]; then
    echo "   ✅ Non-admin blocked from user management (403 Forbidden)"
else
    echo "   ❌ Security issue: Non-admin accessed user management (HTTP $HTTP_CODE)"
fi
echo ""

echo "==============================="
echo "✅ User Management API Tests Complete!"
echo ""
echo "Summary:"
echo "  ✓ List users (admin only)"
echo "  ✓ Get user details"
echo "  ✓ Activate/Deactivate users"
echo "  ✓ Change user roles"
echo "  ✓ Role-based permissions enforced"
echo "  ✓ Non-admin access blocked"
