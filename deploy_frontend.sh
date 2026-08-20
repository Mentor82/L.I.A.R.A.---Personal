#!/bin/bash
# ============================================================================
# Liara Frontend Auto-Deploy Script
# Builds + deploys React frontend in ~5 seconds
# ============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DIST_DIR="$FRONTEND_DIR/dist"
DEPLOY_DIR="/opt/liara/frontend/dist"

echo ""
echo "🚀 =============================================="
echo "🚀 Liara Frontend Auto-Deploy"
echo "🚀 =============================================="
echo ""

# 1. Build Frontend
echo "📦 Building React Frontend..."
cd "$FRONTEND_DIR"

# DIST_DIR and DEPLOY_DIR are the same path here, and the previous run's chown to
# www-data (step 4) leaves it un-writable for vite's own cleanup as the normal user.
# Reset it with sudo before building so vite always starts from a clean, writable dir.
if [ -d "$DIST_DIR" ]; then
    sudo rm -rf "$DIST_DIR"
fi

if ! npm run build; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build complete"
echo ""

# 2. Backup + Clear old dist
echo "🗑️  Preparing deployment directory..."
if [ -d "$DEPLOY_DIR" ]; then
    # Don't delete if it's the same directory
    if [ "$DIST_DIR" != "$DEPLOY_DIR" ]; then
        sudo rm -rf "$DEPLOY_DIR"/*
        echo "✅ Old files removed"
    else
        echo "⚠️  Source and destination are the same, skipping clear"
    fi
else
    echo "⚠️  Deploy directory doesn't exist, creating..."
    sudo mkdir -p "$DEPLOY_DIR"
fi
echo ""

# 3. Copy new build
echo "📂 Copying new build..."
if [ "$DIST_DIR" != "$DEPLOY_DIR" ]; then
    sudo cp -r "$DIST_DIR"/* "$DEPLOY_DIR"/
    echo "✅ Files copied"
else
    echo "✅ Build already in place"
fi
echo ""

# 4. Set permissions
echo "🔐 Setting permissions..."
sudo chown -R www-data:www-data "$DEPLOY_DIR"
sudo chmod -R 755 "$DEPLOY_DIR"
echo "✅ Permissions set"
echo ""

# 5. Reload Nginx
echo "🔄 Reloading Nginx..."
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "❌ Nginx config test failed!"
    exit 1
fi

echo ""
echo "🎉 =============================================="
echo "🎉 Frontend deployed successfully!"
echo "🎉 =============================================="
echo ""
echo "📊 Deployment Summary:"
echo "   Build Location:  $DIST_DIR"
echo "   Deploy Location: $DEPLOY_DIR"
echo "   Files Deployed:  $(find "$DEPLOY_DIR" -type f | wc -l)"
echo ""
echo "🌐 Frontend available at: https://liara.mw-dresden.de"
echo ""
