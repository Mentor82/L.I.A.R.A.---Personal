#!/bin/bash
#
# Liara SSE Server Restart
# ==========================
# Restarts liara-sse.service - a separate plain-uvicorn process (see
# start_sse_server.sh) that nginx routes /api/chat/stream to directly
# (a more specific location block than the generic /api/ -> liara-backend
# proxy, see /etc/nginx/sites-available/liara). It runs the exact same
# main:app as liara-backend, just as its own process on port 8101 - so
# code changes under app/* need THIS restarted too, not just liara-backend.
#
# Plain `uvicorn --workers N` has no SIGHUP graceful-reload equivalent like
# Gunicorn does, so this is always a hard restart - a brief connection drop
# for anyone streaming a chat response at that exact moment.
#
# Safe to call synchronously (unlike restart_backend.sh's systemd-run
# detour): AI-exec commands run under liara-backend/gunicorn on port 8100
# (see nginx's generic /api/ block), a completely different process tree
# from liara-sse, so restarting this service can't kill the calling job.
#
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔄 Restarting liara-sse.service...${NC}"
sudo systemctl restart liara-sse

# Give the new workers a moment to come up before checking status.
sleep 2

if systemctl is-active --quiet liara-sse; then
    echo -e "${GREEN}✅ liara-sse.service is running${NC}"
else
    echo -e "${RED}❌ liara-sse.service failed to start${NC}"
    sudo systemctl status liara-sse --no-pager -l
    exit 1
fi
