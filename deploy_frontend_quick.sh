#!/bin/bash
# Quick deploy script for Liara frontend

echo "🚀 Deploying Liara Frontend..."

# Copy files (will prompt for sudo password once)
sudo cp -r /opt/liara/frontend/dist/* /var/www/liara/

if [ $? -eq 0 ]; then
    echo "✅ Frontend deployed successfully!"
    echo ""
    echo "📦 Changes:"
    echo "  • Dynamische responsive Größen (clamp())"
    echo "  • Navigation: sticky, 220-260px breit"
    echo "  • Spacing: 50% reduziert, viewport-basiert"
    echo "  • Terminal: 500-700px Höhe, auto-scaling"
    echo "  • Alle Abstände passen sich an Bildschirmgröße an"
else
    echo "❌ Deployment failed!"
    exit 1
fi
