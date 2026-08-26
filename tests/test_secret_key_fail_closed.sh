#!/bin/bash
# Regression test for issue #6 (JWT secret fail-closed): app/core/security.py
# must refuse to import under a missing/placeholder/too-short LIARA_SECRET_KEY,
# and must import cleanly with a valid one. Pure import-time check, no running
# server/DB connection needed (SQLAlchemy's create_engine() is lazy).
#
# Each scenario runs from its own scratch directory with its own minimal
# .env - core/database.py calls python-dotenv's load_dotenv() (no path arg,
# searches upward from cwd) as an import-time side effect of importing
# core.security (via api.models.base_models), so merely unsetting the shell
# env var isn't enough on its own: dotenv would just refill it from the
# real /opt/liara/app/.env on every import. Running from an unrelated
# scratch cwd with PYTHONPATH pointed at the app means dotenv finds only
# the scenario's own synthetic .env.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../app" && pwd)"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

echo "🧪 Liara JWT-Secret Fail-Closed Test (issue #6)"
echo "=================================================="
echo ""

# $1 = .env file content for this scenario (may be empty for "no key at all")
run_with_env() {
    printf '%s\n' "$1" > "$SCRATCH/.env"
    (cd "$SCRATCH" && PYTHONPATH="$APP_DIR" env -u LIARA_SECRET_KEY python3 -c "import core.security") 2>/dev/null
}

check_fails() {
    local label="$1"
    local env_content="$2"
    if run_with_env "$env_content"; then
        echo "   ❌ SECURITY ISSUE: $label was accepted, should have failed"
        return 1
    else
        echo "   ✅ $label correctly rejected"
        return 0
    fi
}

FAILED=0

echo "1️⃣  Missing LIARA_SECRET_KEY (no line in .env at all)..."
check_fails "missing secret" "" || FAILED=1
echo ""

echo "2️⃣  Known development placeholder..."
check_fails "placeholder secret" "LIARA_SECRET_KEY=your-secret-key-change-in-production-use-env-var" || FAILED=1
echo ""

echo "3️⃣  Too-short secret (16 chars)..."
check_fails "too-short secret" "LIARA_SECRET_KEY=short1234567890a" || FAILED=1
echo ""

echo "4️⃣  Valid secret (64 hex chars) must import cleanly..."
VALID_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
if run_with_env "LIARA_SECRET_KEY=$VALID_SECRET"; then
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
