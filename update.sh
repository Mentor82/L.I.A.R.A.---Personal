#!/bin/bash
#
# Liara Auto-Update
# ==================
# Pulls the latest changes and only restarts/redeploys what actually needs it:
#   - Backend (anything under app/ changed)  -> ./reload_backend.sh + ./restart_sse.sh
#     (liara-sse is a separate process running the same app/* code - nginx
#     routes /api/chat/stream to it directly, so it needs restarting too)
#   - Frontend (frontend/* changed) -> ./deploy_frontend.sh
#
# Usage:
#   ./update.sh
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Liara Auto-Update                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Not a git repository: $SCRIPT_DIR${NC}"
    exit 1
fi

BEFORE=$(git rev-parse HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo -e "${BLUE}📥 Pulling latest changes (origin/$BRANCH)...${NC}"
git pull --ff-only origin "$BRANCH"
echo ""

AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    echo -e "${GREEN}✅ Already up to date ($BEFORE). Nothing to do.${NC}"
    exit 0
fi

echo -e "${BLUE}📋 Changed files ($BEFORE..$AFTER):${NC}"
CHANGED_FILES=$(git diff --name-only "$BEFORE" "$AFTER")
echo "$CHANGED_FILES" | sed 's/^/   /'
echo ""

BACKEND_CHANGED=false
FRONTEND_CHANGED=false

while IFS= read -r FILE; do
    [ -z "$FILE" ] && continue
    if [[ "$FILE" == app/* ]]; then
        BACKEND_CHANGED=true
    fi
    if [[ "$FILE" == frontend/* ]]; then
        FRONTEND_CHANGED=true
    fi
done <<< "$CHANGED_FILES"

BACKEND_OK=true
FRONTEND_OK=true
SSE_OK=true

# Frontend goes first, backend restart last: restarting the backend drops
# active connections (and, if this script is ever launched from a request
# handled by that same backend - e.g. a future web "run update" button - it
# can kill this very script's process tree). Doing the less disruptive,
# easier-to-verify step first means a frontend build failure never leaves
# the backend restarted for nothing, and the backend step being last means
# it's the very last thing that could possibly cut this script off.
#
# Each step is guarded with `if ! ...` so a failure in one (set -e would
# otherwise abort the whole script right here) never prevents the other,
# unrelated step from still running.
if [ "$FRONTEND_CHANGED" = true ]; then
    echo -e "${YELLOW}🎨 Frontend-Änderungen erkannt (frontend/*) - deploye Frontend...${NC}"
    if ! ./deploy_frontend.sh; then
        echo -e "${RED}❌ Frontend-Deploy fehlgeschlagen!${NC}"
        FRONTEND_OK=false
    fi
    echo ""
else
    echo -e "${BLUE}ℹ️  Keine Frontend-Änderungen, Deploy übersprungen.${NC}"
    echo ""
fi

if [ "$BACKEND_CHANGED" = true ]; then
    echo -e "${YELLOW}🔧 Backend-Änderungen erkannt (app/*) - reloade Backend (graceful, zero-downtime)...${NC}"
    if ! ./reload_backend.sh; then
        echo -e "${RED}❌ Backend-Reload fehlgeschlagen!${NC}"
        BACKEND_OK=false
    fi
    echo ""

    # liara-sse runs the same app/* code as its own separate uvicorn process
    # (nginx routes /api/chat/stream to it directly, not to liara-backend -
    # see restart_sse.sh) - it needs restarting too, or it keeps serving
    # chat responses from stale, pre-update code indefinitely.
    echo -e "${YELLOW}🔧 Restarte SSE-Server (separater Prozess, gleiche app/*-Codebasis)...${NC}"
    if ! ./restart_sse.sh; then
        echo -e "${RED}❌ SSE-Server-Restart fehlgeschlagen!${NC}"
        SSE_OK=false
    fi
    echo ""
else
    echo -e "${BLUE}ℹ️  Keine Backend-Änderungen, Reload übersprungen.${NC}"
    echo ""
fi

if [ "$BACKEND_OK" = true ] && [ "$FRONTEND_OK" = true ] && [ "$SSE_OK" = true ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Update abgeschlossen! ✅              ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   Update mit Fehlern abgeschlossen! ⚠️   ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    exit 1
fi
