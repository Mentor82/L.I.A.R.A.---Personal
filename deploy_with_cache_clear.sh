#!/bin/bash
# Deploy with cache clearing

echo "🧹 Clearing browser cache headers..."
echo "🚀 Building and deploying..."

cd /opt/liara/frontend
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📦 Deploying to /var/www/liara..."
    
    # Clear old files first
    sudo rm -rf /var/www/liara/*
    
    # Copy new files
    sudo cp -r dist/* /var/www/liara/
    
    # Set proper permissions
    sudo chown -R www-data:www-data /var/www/liara/
    sudo chmod -R 755 /var/www/liara/
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📋 Changes:"
    echo "  • Cache-Control Headers hinzugefügt"
    echo "  • Sidebar funktioniert auf Desktop UND Tablet"
    echo "  • Responsive Breakpoints entfernt"
    echo "  • Navigation bleibt sticky auf allen Geräten"
    echo ""
    echo "🔄 Drücke Strg+Shift+R (Hard Reload) im Browser!"
else
    echo "❌ Build failed!"
    exit 1
fi
