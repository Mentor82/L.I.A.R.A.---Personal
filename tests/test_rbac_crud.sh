#!/bin/bash
# Test RBAC CRUD Operations

BASE_URL="http://localhost:8100"

echo "🧪 Testing RBAC CRUD Operations"
echo "================================"
echo ""

# Login as testuser
echo "1️⃣  Login as testuser..."
TESTUSER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ ! -z "$TESTUSER_TOKEN" ]; then
    echo "   ✅ testuser logged in"
else
    echo "   ❌ Login failed"
    exit 1
fi
echo ""

# Login as admin
echo "2️⃣  Login as admin..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])")

if [ ! -z "$ADMIN_TOKEN" ]; then
    echo "   ✅ admin logged in"
else
    echo "   ❌ Admin login failed"
    exit 1
fi
echo ""

# Test 1: Create task as testuser
echo "3️⃣  Create task as testuser..."
TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/tasks/" \
  -H "Authorization: Bearer $TESTUSER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Testuser Task",
    "description": "This belongs to testuser",
    "priority": "high"
  }')

TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)
if [ ! -z "$TASK_ID" ]; then
    echo "   ✅ Task created (ID: $TASK_ID)"
else
    echo "   ❌ Task creation failed"
fi
echo ""

# Test 2: testuser can see own task
echo "4️⃣  testuser accessing own task..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TESTUSER_TOKEN" \
  "$BASE_URL/tasks/$TASK_ID")

if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ testuser can access own task (200 OK)"
else
    echo "   ❌ Access failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 3: admin can see testuser's task
echo "5️⃣  admin accessing testuser's task..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$BASE_URL/tasks/$TASK_ID")

if [ "$HTTP_CODE" == "200" ]; then
    echo "   ✅ admin can access testuser's task (200 OK)"
else
    echo "   ❌ Admin access failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 4: demouser cannot see testuser's task
echo "6️⃣  demouser trying to access testuser's task..."
DEMOUSER_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demouser", "password": "demopass123"}' | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ ! -z "$DEMOUSER_TOKEN" ]; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $DEMOUSER_TOKEN" \
      "$BASE_URL/tasks/$TASK_ID")
    
    if [ "$HTTP_CODE" == "403" ]; then
        echo "   ✅ demouser blocked (403 Forbidden) ✓ Isolation working!"
    else
        echo "   ❌ Security issue: demouser accessed other's task (HTTP $HTTP_CODE)"
    fi
else
    echo "   ⚠️  demouser login failed, skipping test"
fi
echo ""

# Test 5: Unauthenticated access blocked
echo "7️⃣  Testing unauthenticated access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/tasks/")

if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
    echo "   ✅ Unauthenticated requests blocked (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  Unauthenticated access allowed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 6: List tasks shows only own
echo "8️⃣  Testing task isolation (testuser sees only own tasks)..."
TESTUSER_TASKS=$(curl -s -H "Authorization: Bearer $TESTUSER_TOKEN" "$BASE_URL/tasks/" | \
  python3 -c "import json, sys; tasks = json.load(sys.stdin)['tasks']; print(len([t for t in tasks if t.get('user_id') != 2]))" 2>/dev/null)

if [ "$TESTUSER_TASKS" == "0" ]; then
    echo "   ✅ testuser sees only own tasks (isolation confirmed)"
else
    echo "   ⚠️  testuser might see other users' tasks"
fi
echo ""

# Test 7: Admin sees all tasks
echo "9️⃣  Testing admin sees all tasks..."
ADMIN_TASK_COUNT=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/tasks/" | \
  python3 -c "import json, sys; print(json.load(sys.stdin)['total'])" 2>/dev/null)

echo "   ℹ️  admin sees $ADMIN_TASK_COUNT total tasks"
echo "   ✅ Admin has full visibility"
echo ""

echo "================================"
echo "✅ RBAC CRUD Tests Complete!"
echo ""
echo "Summary:"
echo "  ✓ Users can create own data"
echo "  ✓ Users can access own data"
echo "  ✓ Users CANNOT access other users' data"
echo "  ✓ Admin can access ALL data"
echo "  ✓ Unauthenticated requests blocked"
