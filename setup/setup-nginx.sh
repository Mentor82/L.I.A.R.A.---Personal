#!/bin/bash
# Liara nginx Reverse Proxy Setup Script

set -e

echo "🔧 Installing nginx..."
sudo apt update
sudo apt install -y nginx

echo "🔐 Generating self-signed SSL certificate..."
sudo mkdir -p /etc/ssl/private
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/liara.key \
    -out /etc/ssl/certs/liara.crt \
    -subj "/C=DE/ST=NRW/L=YourCity/O=Liara/CN=liara"

sudo chmod 600 /etc/ssl/private/liara.key

echo "📋 Copying nginx configuration..."
sudo cp /opt/liara/setup/nginx-liara.conf /etc/nginx/sites-available/liara

echo "🔗 Enabling site..."
sudo ln -sf /etc/nginx/sites-available/liara /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Remove default site

echo "✅ Testing nginx configuration..."
sudo nginx -t

echo "🔄 Restarting nginx..."
sudo systemctl restart nginx
sudo systemctl enable nginx

echo "📊 Status:"
sudo systemctl status nginx --no-pager

echo ""
echo "✅ nginx Reverse Proxy Setup Complete!"
echo ""
echo "📝 Next Steps:"
echo "1. Build Frontend: cd /opt/liara/frontend && npm run build"
echo "2. Access Liara: https://liara or https://192.168.178.50"
echo "3. Backend API: https://liara/api/info"
echo ""
echo "⚠️  Browser wird Warnung wegen selbstsigniertem Zertifikat zeigen"
echo "   Für Produktion: Let's Encrypt Zertifikat verwenden"
echo ""
echo "🔒 Basic Auth wird weiterhin vom FastAPI Backend gehandhabt"
