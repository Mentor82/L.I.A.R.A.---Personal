#!/bin/bash
# Liara Backend Restart Script
# Multi-Worker with Gunicorn + Uvicorn Workers

# Detect CPU cores
CPU_CORES=$(nproc)
# Use (cores * 2) + 1 for optimal worker count
WORKERS=$((CPU_CORES * 2 + 1))

echo "🔄 Stopping old backend processes..."
pkill -9 -f "uvicorn main:app" || true
pkill -9 -f "gunicorn main:app" || true
sleep 3

echo "🚀 Starting backend with $WORKERS workers via Gunicorn (CPU cores: $CPU_CORES)..."
cd /opt/liara/app
/opt/liara/venv/bin/gunicorn main:app \
  --workers $WORKERS \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8100 \
  --access-logfile /tmp/liara_access.log \
  --error-logfile /tmp/liara_error.log \
  --log-level info \
  --daemon

sleep 3

echo "✅ Backend started! Checking status..."
curl -s http://localhost:8100/ 2>&1 | head -5 || echo "⚠️ Health check failed"

echo ""
echo "📋 Access Logs: tail -f /tmp/liara_access.log"
echo "📋 Error Logs: tail -f /tmp/liara_error.log"
echo "🔍 Status: lsof -i :8100"
echo "📍 Workers: $WORKERS"
echo "📍 Master PID: $(pgrep -f 'gunicorn main:app' | head -1)"
echo "📍 Worker PIDs: $(pgrep -f 'gunicorn main:app' | tail -n +2 | tr '\n' ' ')"
