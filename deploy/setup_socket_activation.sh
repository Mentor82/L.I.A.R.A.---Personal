#!/bin/bash
#
# Setup Script for Liara Systemd Socket Activation & Unix Domain Socket
# ======================================================================
# Installs liara-backend.socket and updated liara-backend.service,
# activates the socket, updates nginx upstream, and verifies permissions.
#
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}🔧 Installing Systemd Socket Activation for Liara...${NC}"

# 1. Copy socket and service files to /etc/systemd/system
sudo cp "$REPO_DIR/deploy/systemd/liara-backend.socket" /etc/systemd/system/liara-backend.socket
sudo cp "$REPO_DIR/deploy/systemd/liara-backend.service" /etc/systemd/system/liara-backend.service
sudo chmod 644 /etc/systemd/system/liara-backend.socket /etc/systemd/system/liara-backend.service

# 2. Copy nginx configuration
sudo cp "$REPO_DIR/deploy/nginx/liara.conf" /etc/nginx/sites-available/liara
sudo ln -sf /etc/nginx/sites-available/liara /etc/nginx/sites-enabled/liara

# 3. Reload systemd daemon
echo -e "${BLUE}🔄 Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

# 4. Enable and start socket
echo -e "${BLUE}🔌 Enabling and starting liara-backend.socket...${NC}"
sudo systemctl enable liara-backend.socket
sudo systemctl restart liara-backend.socket

# 5. Reload backend service
echo -e "${BLUE}🚀 Reloading/Starting liara-backend.service...${NC}"
sudo systemctl restart liara-backend.service

# 6. Test and reload Nginx
echo -e "${BLUE}🌐 Testing Nginx configuration...${NC}"
sudo nginx -t
sudo systemctl reload nginx

# 7. Verification
echo -e "${BLUE}🔍 Verifying Unix Domain Socket connectivity...${NC}"
sleep 2
if [ -S /run/liara/liara-backend.sock ]; then
    echo -e "${GREEN}✅ Unix socket /run/liara/liara-backend.sock is active!${NC}"
    ls -la /run/liara/liara-backend.sock
else
    echo -e "${RED}❌ Unix socket /run/liara/liara-backend.sock not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✨ Zero-Downtime Socket Activation successfully set up!${NC}"
