#!/bin/bash
#
# Liara Patch Applicator
# Applies a patch created by create_patch.sh
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Liara Patch Applicator v1.0        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check arguments
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./apply_patch.sh <patch.tar.gz|patch_directory>${NC}"
    echo -e "${YELLOW}Example: ./apply_patch.sh patches/20251203_v2.6.2.tar.gz${NC}"
    echo ""
    echo -e "${BLUE}Available patches:${NC}"
    ls -1t patches/*.tar.gz 2>/dev/null | head -5 || echo "  No patches found"
    echo ""
    exit 1
fi

PATCH_INPUT="$1"

# Extract if tarball
if [[ $PATCH_INPUT == *.tar.gz ]]; then
    echo -e "${BLUE}📦 Extracting patch...${NC}"
    cd patches
    tar -xzf "$(basename "$PATCH_INPUT")"
    PATCH_DIR=$(basename "$PATCH_INPUT" .tar.gz)
    cd ..
    PATCH_PATH="patches/$PATCH_DIR"
    echo -e "${GREEN}   ✅ Extracted to $PATCH_PATH${NC}"
else
    PATCH_PATH="$PATCH_INPUT"
fi

# Verify patch directory
if [ ! -d "$PATCH_PATH" ]; then
    echo -e "${RED}❌ Patch directory not found: $PATCH_PATH${NC}"
    exit 1
fi

if [ ! -f "$PATCH_PATH/PATCH_INFO.txt" ]; then
    echo -e "${RED}❌ Invalid patch: PATCH_INFO.txt not found${NC}"
    exit 1
fi

# Display patch info
echo ""
echo -e "${BLUE}📋 Patch Information:${NC}"
cat "$PATCH_PATH/PATCH_INFO.txt" | head -20
echo ""

# Confirm installation
read -p "Apply this patch? (y/n): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Patch installation cancelled${NC}"
    exit 0
fi

# Recommend backup
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Create a backup before proceeding!${NC}"
read -p "Have you created a backup? (y/n): " HAS_BACKUP
if [[ ! $HAS_BACKUP =~ ^[Yy]$ ]]; then
    echo ""
    read -p "Create backup now? (y/n): " CREATE_BACKUP
    if [[ $CREATE_BACKUP =~ ^[Yy]$ ]]; then
        VERSION=$(basename "$PATCH_PATH" | cut -d'_' -f3-)
        ./create_backup.sh "pre_${VERSION}" << EOF
n
EOF
        echo ""
    else
        echo -e "${RED}❌ Backup required. Aborting.${NC}"
        exit 1
    fi
fi

# Run pre-install script
if [ -f "$PATCH_PATH/pre_install.sh" ]; then
    echo ""
    echo -e "${BLUE}🔧 Running pre-install script...${NC}"
    cd "$PATCH_PATH"
    bash pre_install.sh
    cd - > /dev/null
    echo -e "${GREEN}   ✅ Pre-install complete${NC}"
fi

# Apply SQL migrations
if [ -d "$PATCH_PATH/migrations" ] && [ "$(ls -A "$PATCH_PATH/migrations")" ]; then
    echo ""
    echo -e "${BLUE}🗄️  Applying database migrations...${NC}"
    for MIGRATION in "$PATCH_PATH/migrations"/*.sql; do
        if [ -f "$MIGRATION" ]; then
            echo -e "   Applying $(basename "$MIGRATION")..."
            sudo -u postgres psql liara_db < "$MIGRATION"
            echo -e "${GREEN}   ✅ $(basename "$MIGRATION") applied${NC}"
        fi
    done
fi

# Copy files
if [ -d "$PATCH_PATH/files" ] && [ "$(ls -A "$PATCH_PATH/files")" ]; then
    echo ""
    echo -e "${BLUE}📁 Copying files...${NC}"
    
    # Find all files in patch
    cd "$PATCH_PATH/files"
    FILES=$(find . -type f)
    cd - > /dev/null
    
    for FILE in $FILES; do
        # Remove leading ./
        FILE=${FILE#./}
        SRC="$PATCH_PATH/files/$FILE"
        DEST="/opt/liara/$FILE"
        
        # Create directory if needed
        mkdir -p "$(dirname "$DEST")"
        
        # Backup original file
        if [ -f "$DEST" ]; then
            cp "$DEST" "$DEST.backup_$(date +%s)"
        fi
        
        # Copy new file
        cp "$SRC" "$DEST"
        echo -e "${GREEN}   ✅ $FILE${NC}"
    done
else
    echo -e "${YELLOW}   ⚠️  No files to copy${NC}"
fi

# Run post-install script
if [ -f "$PATCH_PATH/post_install.sh" ]; then
    echo ""
    echo -e "${BLUE}🔄 Running post-install script...${NC}"
    cd "$PATCH_PATH"
    bash post_install.sh
    cd - > /dev/null
    echo -e "${GREEN}   ✅ Post-install complete${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Patch Applied Successfully! ✅     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Check backend logs: tail -f /tmp/liara_backend.log"
echo -e "  2. Test the application"
echo -e "  3. Monitor for errors"
echo ""
echo -e "${YELLOW}Rollback (if needed):${NC}"
echo -e "  cd $PATCH_PATH && ./rollback.sh"
echo ""
echo -e "${BLUE}Backup files (.backup_*) saved in case of issues${NC}"
echo ""
