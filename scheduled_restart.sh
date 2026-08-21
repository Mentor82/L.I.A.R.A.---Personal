#!/bin/bash
#
# Liara Scheduled Backend Restart
# ================================
# Run via `systemd-run --on-active=2s` from restart_backend.sh, as its own
# transient systemd unit owned by PID 1 - NOT as a child of the
# liara-backend.service cgroup. See restart_backend.sh for why that
# indirection exists. Because this runs detached from that cgroup, it's also
# the only place that can safely wait and record whether the restart
# actually succeeded (anything still running inside liara-backend's own
# cgroup at kill time would go down with it).
#
RESULT_LOG="/var/log/liara/restart_result.log"

systemctl restart liara-backend
sleep 2

if systemctl is-active --quiet liara-backend; then
    echo "$(date -Iseconds) OK" >> "$RESULT_LOG"
else
    echo "$(date -Iseconds) FAILED" >> "$RESULT_LOG"
    systemctl status liara-backend --no-pager -l >> "$RESULT_LOG"
fi
