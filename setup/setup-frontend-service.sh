#!/bin/bash
# Setup Frontend als systemd Service

set -e

echo "📦 Installing Frontend Dependencies..."
cd /opt/liara/frontend
npm install

echo "🏗️ Building Frontend..."
npm run build

echo "📝 Creating systemd service file..."
sudo tee /etc/systemd/system/liara-frontend.service > /dev/null << 'EOF'
[Unit]
Description=Liara Frontend Service (Vite Dev Server)
After=network.target

[Service]
Type=simple
User=mirko
WorkingDirectory=/opt/liara/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 5173
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "🚀 Starting and enabling frontend service..."
sudo systemctl enable liara-frontend.service
sudo systemctl start liara-frontend.service

echo ""
echo "✅ Frontend Service Setup Complete!"
echo ""
echo "📊 Status:"
sudo systemctl status liara-frontend.service --no-pager -l
echo ""
echo "📝 Nützliche Befehle:"
echo "  sudo systemctl status liara-frontend.service   - Status prüfen"
echo "  sudo systemctl restart liara-frontend.service  - Neu starten"
echo "  sudo systemctl stop liara-frontend.service     - Stoppen"
echo "  sudo journalctl -u liara-frontend.service -f   - Logs live ansehen"
echo ""
echo "🌐 Frontend erreichbar unter:"
echo "  http://liara:5173"
echo "  http://192.168.178.50:5173"
