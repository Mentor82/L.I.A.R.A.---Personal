#!/bin/bash
#
# Liara Backend Restart
# ======================
# Schedules the liara-backend restart via a detached systemd-run unit
# instead of restarting it directly in THIS process.
#
# Why: this script can itself run as a child of liara-backend.service - e.g.
# the AI-exec feature (terminal_exec_router.py) runs shell commands as a
# background task inside the backend's own gunicorn worker. systemd's
# default KillMode=control-group kills every process in a unit's cgroup on
# restart, including this script and whatever called it. A direct
# `systemctl restart` here could kill that caller before it finishes writing
# its own result to Redis/the audit log, leaving a job stuck at "running"
# forever. Scheduling the actual restart via `systemd-run` (a transient unit
# owned by PID 1, not this cgroup) lets this script - and its caller -
# return and finish cleanly first; the restart still happens moments later
# regardless of what called this script.
#
# Because of that, this script can no longer verify the restart synchronously
# (anything waiting inside liara-backend's own cgroup would go down with it).
# scheduled_restart.sh does that verification instead, from outside the
# cgroup, and logs the result to RESULT_LOG.
#
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESULT_LOG="/var/log/liara/restart_result.log"
UNIT_NAME="liara-backend-restart"

echo -e "${BLUE}🔄 Scheduling liara-backend restart (detached, in ~2s)...${NC}"
sudo systemd-run --on-active=2s --unit="$UNIT_NAME" "$SCRIPT_DIR/scheduled_restart.sh"

echo -e "${GREEN}✅ Restart scheduled.${NC}"
echo -e "${BLUE}ℹ️  This returns immediately by design - the restart itself happens"
echo -e "   a couple seconds from now, outside this process's cgroup, so a"
echo -e "   caller running inside liara-backend (like the AI-exec feature)"
echo -e "   can finish and save its own result first.${NC}"
echo -e "${BLUE}   Verify success separately in a few seconds:"
echo -e "   tail -1 $RESULT_LOG   (or check /admin/health)${NC}"
