#!/bin/bash
#
# Liara Backend Graceful Reload
# ===============================
# Sends SIGHUP to the Gunicorn master via `systemctl reload` instead of
# stopping/starting the unit. The master keeps listening on the port the
# whole time - it spins up new workers with the updated code and only
# retires the old ones once they've finished in-flight requests - so nginx
# never has a dead upstream to proxy to (no 502 window).
#
# This also sidesteps the cgroup-kill race that restart_backend.sh has to
# work around: `systemctl reload` never stops the unit, so
# KillMode=control-group never triggers, so a caller running inside
# liara-backend itself (e.g. the AI-exec feature) is never at risk of being
# killed mid-flight. No systemd-run detour needed here.
#
# Only reloads Python code. Changes to requirements.txt, the systemd unit
# itself, or environment variables need a real restart - use
# restart_backend.sh for those (rare).
#
# Requires ExecReload=/bin/kill -HUP $MAINPID in liara-backend's systemd
# unit (added manually, one-time).
#
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔄 Reloading liara-backend (graceful, zero-downtime)...${NC}"
sudo systemctl reload liara-backend

# Give the new workers a moment to come up before checking status.
sleep 3

if systemctl is-active --quiet liara-backend; then
    echo -e "${GREEN}✅ liara-backend.service reloaded and running${NC}"
else
    echo -e "${RED}❌ liara-backend.service is not active after reload${NC}"
    sudo systemctl status liara-backend --no-pager -l
    exit 1
fi
