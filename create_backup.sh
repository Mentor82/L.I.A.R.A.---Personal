#!/bin/bash
#
# Liara Backup Script
# Creates a complete backup of Liara including DB, code, docs, and configs
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Liara Backup Creator v1.0          ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Get version tag (optional)
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./create_backup.sh [version_tag]${NC}"
    echo -e "${YELLOW}Example: ./create_backup.sh v2.6.1_user_isolation_fix${NC}"
    echo ""
    read -p "Enter version tag (or press Enter for 'manual_backup'): " VERSION_TAG
    if [ -z "$VERSION_TAG" ]; then
        VERSION_TAG="manual_backup"
    fi
else
    VERSION_TAG="$1"
fi

# Create backup directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}_${VERSION_TAG}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}📦 Creating backup: $BACKUP_DIR${NC}"
echo ""

# 1. PostgreSQL Database
echo -e "${BLUE}🗄️  Backing up PostgreSQL database...${NC}"
sudo -u postgres pg_dump liara_db > "$BACKUP_DIR/liara_db_dump.sql"
DB_SIZE=$(du -sh "$BACKUP_DIR/liara_db_dump.sql" | cut -f1)
echo -e "${GREEN}   ✅ Database backed up ($DB_SIZE)${NC}"

# 2. App Code
echo -e "${BLUE}📁 Backing up app code...${NC}"
cp -r app "$BACKUP_DIR/"
echo -e "${GREEN}   ✅ App code backed up${NC}"

# 3. Documentation
echo -e "${BLUE}📚 Backing up documentation...${NC}"
cp -r docs "$BACKUP_DIR/"
echo -e "${GREEN}   ✅ Documentation backed up${NC}"

# 4. Markdown files
echo -e "${BLUE}📋 Backing up markdown files...${NC}"
cp *.md "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}   ✅ Markdown files backed up${NC}"

# 5. Scripts
echo -e "${BLUE}🔧 Backing up scripts...${NC}"
cp *.sh "$BACKUP_DIR/" 2>/dev/null || true
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}   ✅ Scripts backed up${NC}"

# 6. System configs
echo -e "${BLUE}⚙️  Backing up system configs...${NC}"
sudo cp /etc/systemd/system/liara*.service "$BACKUP_DIR/" 2>/dev/null || true
sudo cp /etc/nginx/sites-available/liara "$BACKUP_DIR/nginx-liara.conf" 2>/dev/null || true
echo -e "${GREEN}   ✅ System configs backed up${NC}"

# 7. Frontend config
echo -e "${BLUE}🎨 Backing up frontend config...${NC}"
cp frontend/package.json "$BACKUP_DIR/" 2>/dev/null || true
cp frontend/vite.config.js "$BACKUP_DIR/" 2>/dev/null || true
cp frontend/eslint.config.js "$BACKUP_DIR/" 2>/dev/null || true
echo -e "${GREEN}   ✅ Frontend config backed up${NC}"

# 8. Create backup info file
echo -e "${BLUE}📝 Creating backup info file...${NC}"
cat > "$BACKUP_DIR/BACKUP_INFO.txt" << EOF
Liara Backup
============
Date: $(date)
Version Tag: $VERSION_TAG
Hostname: $(hostname)
User: $(whoami)

Backup Contents:
----------------
✓ PostgreSQL database dump (liara_db)
✓ Complete app/ directory with all Python code
✓ Documentation (docs/)
✓ Markdown files (README.md, CHANGELOG.md, etc.)
✓ Shell scripts (*.sh)
✓ Docker Compose configuration
✓ Systemd service files
✓ Nginx configuration
✓ Frontend configuration files

Database: PostgreSQL liara_db ($DB_SIZE dump)
Neo4j: Not backed up (graph data on localhost:7687)
Redis: Not backed up (session data, ephemeral)

System Info:
------------
Backend: Running on port 8100
Frontend: Served via nginx
Python: $(python3 --version 2>&1)
Node: $(node --version 2>&1)

Restore Instructions:
---------------------
1. Database: sudo -u postgres psql liara_db < liara_db_dump.sql
2. App: cp -r app /opt/liara/
3. Docs: cp -r docs /opt/liara/
4. Services: sudo cp *.service /etc/systemd/system/
5. Nginx: sudo cp nginx-liara.conf /etc/nginx/sites-available/liara
6. Reload: sudo systemctl daemon-reload && sudo systemctl restart liara nginx

Notes:
------
- Neo4j data must be backed up separately if needed
- Redis session data is ephemeral and not included
- Check CHANGELOG.md for version-specific changes
- Frontend build artifacts not included (run npm run build after restore)
EOF
echo -e "${GREEN}   ✅ Backup info created${NC}"

# Calculate total size
echo ""
echo -e "${BLUE}📊 Calculating backup size...${NC}"
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Backup Complete! ✅             ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo ""
echo -e "  ${BLUE}Location:${NC} $BACKUP_DIR"
echo -e "  ${BLUE}Size:${NC}     $TOTAL_SIZE"
echo -e "  ${BLUE}Database:${NC} $DB_SIZE"
echo ""

# List contents
echo -e "${BLUE}📂 Backup Contents:${NC}"
ls -lh "$BACKUP_DIR" | tail -n +2 | head -15

# Check if there are more files
FILE_COUNT=$(ls -1 "$BACKUP_DIR" | wc -l)
if [ $FILE_COUNT -gt 15 ]; then
    echo "   ... and $((FILE_COUNT - 15)) more files"
fi

echo ""
echo -e "${GREEN}✨ Backup saved to: backups/${TIMESTAMP}_${VERSION_TAG}${NC}"
echo ""

# Offer to create ZIP
read -p "Create ZIP archive? (y/n): " CREATE_ZIP
if [[ $CREATE_ZIP =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}📦 Creating ZIP archive...${NC}"
    cd backups
    zip -r -q "${TIMESTAMP}_${VERSION_TAG}.zip" "${TIMESTAMP}_${VERSION_TAG}"
    ZIP_SIZE=$(du -sh "${TIMESTAMP}_${VERSION_TAG}.zip" | cut -f1)
    cd ..
    echo -e "${GREEN}   ✅ ZIP created: backups/${TIMESTAMP}_${VERSION_TAG}.zip ($ZIP_SIZE)${NC}"
    echo ""
fi

echo -e "${BLUE}Done! 🎉${NC}"
