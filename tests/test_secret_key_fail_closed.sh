#!/bin/bash
# Regression test for issue #6 (JWT secret fail-closed): app/core/security.py
# must refuse to import under a missing/placeholder/too-short LIARA_SECRET_KEY,
# and must import cleanly with a valid one. Pure import-time check, no server
# needed - run this from the repo's app/ directory (or adjust APP_DIR below).

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../app" && pwd)"
cd "$APP_DIR" || exit 1

echo "🧪 Liara JWT-Secret Fail-Closed Test (issue #6)"
echo "=================================================="
echo ""

check_fails() {
    local label="$1"
    shift
    if env -u LIARA_SECRET_KEY "$@" python3 -c "import core.security" 2>/dev/null; then
        echo "   ❌ SECURITY ISSUE: $label was accepted, should have failed"
        return 1
    else
        echo "   ✅ $label correctly rejected"
        return 0
    fi
}

FAILED=0

echo "1️⃣  Missing LIARA_SECRET_KEY..."
check_fails "missing secret" || FAILED=1
echo ""

echo "2️⃣  Known development placeholder..."
check_fails "placeholder secret" env LIARA_SECRET_KEY="your-secret-key-change-in-production-use-env-var" || FAILED=1
echo ""

echo "3️⃣  Too-short secret (16 chars)..."
check_fails "too-short secret" env LIARA_SECRET_KEY="short1234567890a" || FAILED=1
echo ""

echo "4️⃣  Valid secret (64 hex chars) must import cleanly..."
VALID_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
if env LIARA_SECRET_KEY="$VALID_SECRET" python3 -c "import core.security" 2>/dev/null; then
    echo "   ✅ Valid secret accepted"
else
    echo "   ❌ REGRESSION: valid secret was rejected"
    FAILED=1
fi
echo ""

echo "=================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "✅ JWT-Secret Fail-Closed Tests Complete"
else
    echo "❌ One or more checks failed"
    exit 1
fi
