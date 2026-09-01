#!/bin/bash
# ============================================================================
# Liara SSE Streaming Server (Pure Uvicorn - No Buffering)
# Dedicated server for Server-Sent Events with immediate streaming
# Multi-worker for concurrent users
# Called by systemd service: liara-sse.service
# ============================================================================

cd /opt/liara/app
if [ -d "/opt/liara/venv314" ]; then
    source /opt/liara/venv314/bin/activate
else
    source /opt/liara/venv/bin/activate
fi

# Fixed worker count for stability
WORKERS=3

echo "Starting SSE Server with $WORKERS workers..."

# Pure Uvicorn with multiple workers for concurrent streaming
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8101 \
    --workers $WORKERS \
    --log-level info \
    --access-log \
    --no-server-header \
    --timeout-keep-alive 300 \
    --limit-concurrency 1000
