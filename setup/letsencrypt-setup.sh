#!/bin/bash
# Let's Encrypt SSL Setup (für öffentliche Domains)
# Nur verwenden wenn du eine echte Domain hast!

set -e

DOMAIN="your-domain.com"  # ANPASSEN!
EMAIL="your-email@example.com"  # ANPASSEN!

echo "⚠️  This script is for PUBLIC domains only!"
echo "   Domain: $DOMAIN"
echo "   Email: $EMAIL"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo "📦 Installing certbot..."
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

echo "🔐 Obtaining SSL certificate..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN \
    --non-interactive --agree-tos -m $EMAIL

echo "🔄 Auto-renewal setup..."
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

echo "✅ Let's Encrypt SSL Certificate installed!"
echo "   Certificate auto-renews via certbot.timer"
