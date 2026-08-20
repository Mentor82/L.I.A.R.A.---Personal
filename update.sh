#!/bin/bash
#
# Liara Auto-Update
# ==================
# Pulls the latest changes and only restarts/redeploys what actually needs it:
#   - Backend (app/*.py changed)  -> ./restart_backend.sh
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
    if [[ "$FILE" == app/*.py ]]; then
        BACKEND_CHANGED=true
    fi
    if [[ "$FILE" == frontend/* ]]; then
        FRONTEND_CHANGED=true
    fi
done <<< "$CHANGED_FILES"

if [ "$BACKEND_CHANGED" = true ]; then
    echo -e "${YELLOW}🔧 Backend-Änderungen erkannt (app/*.py) - restarte Backend...${NC}"
    ./restart_backend.sh
    echo ""
else
    echo -e "${BLUE}ℹ️  Keine Backend-Änderungen, Restart übersprungen.${NC}"
    echo ""
fi

if [ "$FRONTEND_CHANGED" = true ]; then
    echo -e "${YELLOW}🎨 Frontend-Änderungen erkannt (frontend/*) - deploye Frontend...${NC}"
    ./deploy_frontend.sh
    echo ""
else
    echo -e "${BLUE}ℹ️  Keine Frontend-Änderungen, Deploy übersprungen.${NC}"
    echo ""
fi

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Update abgeschlossen! ✅              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
