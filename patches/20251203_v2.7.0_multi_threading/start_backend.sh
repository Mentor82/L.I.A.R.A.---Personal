#!/bin/bash
# Liara Backend Start Script
# Multi-Worker Production Mode with Gunicorn

# Detect CPU cores
CPU_CORES=$(nproc)
WORKERS=$((CPU_CORES * 2 + 1))

pkill -9 -f "uvicorn main:app"
pkill -9 -f "gunicorn main:app"
sleep 2

echo "🚀 Starting Liara with $WORKERS Gunicorn workers..."
cd /opt/liara/app
exec /opt/liara/venv/bin/gunicorn main:app \
  --workers $WORKERS \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
