#!/bin/bash
#
# Liara Backend Restart
# Restarts the liara-backend systemd service and verifies it came back up.
#

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔄 Restarting liara-backend.service...${NC}"
sudo systemctl restart liara-backend

# Give the service a moment to come up before checking status
sleep 2

if systemctl is-active --quiet liara-backend; then
    echo -e "${GREEN}✅ liara-backend.service is running${NC}"
else
    echo -e "${RED}❌ liara-backend.service failed to start${NC}"
    sudo systemctl status liara-backend --no-pager -l
    exit 1
fi
