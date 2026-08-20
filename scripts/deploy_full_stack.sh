#!/bin/bash
# Liara Full-Stack Deployment Script
# Builds frontend, restarts backend, reloads nginx

set -e

FRONTEND_DIR="/opt/liara/frontend"
BACKEND_DIR="/opt/liara/app"
NGINX_SERVICE="nginx"

# Build frontend
cd "$FRONTEND_DIR"
echo "🔨 Building frontend..."
npm run build

# Restart backend (Gunicorn/Uvicorn)
echo "🔄 Restarting backend..."
cd "$BACKEND_DIR"
# Optional: adjust to your process manager (systemctl, supervisorctl, pm2, etc.)
# Example for systemd:
# sudo systemctl restart liara-backend
# Example for Gunicorn (if running manually):
# pkill gunicorn && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8100 &

# Reload nginx
if systemctl is-active --quiet $NGINX_SERVICE; then
  echo "🔁 Reloading nginx..."
  sudo systemctl reload $NGINX_SERVICE
else
  echo "⚠️ nginx service not active or not managed by systemd."
fi

echo "✅ Deployment complete. Frontend, backend, and nginx updated."
