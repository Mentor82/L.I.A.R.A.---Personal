#!/bin/bash
#
# Liara Patch Creator v1.0
# ========================
# Creates a deployable patch with changed files, migrations, and scripts
#
# AI Agent Capabilities:
# - Interactive file selection (manual/git/paths)
# - Optional SQL migrations
# - Pre/post-install hooks
# - Automatic rollback script generation
# - Tarball packaging
# - Structured PATCH_INFO.txt for documentation
#
# Usage:
#   ./create_patch.sh <version_tag> [description]
#   ./create_patch.sh v2.6.2_hotfix "Fix user isolation bug"
#
# Non-interactive mode (for AI agents):
#   export PATCH_FILES="app/file1.py,app/file2.py"
#   export PATCH_MIGRATION="ALTER TABLE..."
#   export PATCH_NO_PROMPT=1
#   ./create_patch.sh v2.6.2_hotfix "Description"
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Liara Patch Creator v1.0           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check arguments
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./create_patch.sh <version_tag> [description]${NC}"
    echo -e "${YELLOW}Example: ./create_patch.sh v2.6.2_hotfix \"Fix user isolation bug\"${NC}"
    echo ""
    exit 1
fi

VERSION_TAG="$1"
DESCRIPTION="${2:-Patch for $VERSION_TAG}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PATCH_DIR="patches/${TIMESTAMP}_${VERSION_TAG}"
mkdir -p "$PATCH_DIR/files"
mkdir -p "$PATCH_DIR/migrations"

echo -e "${GREEN}📦 Creating patch: $VERSION_TAG${NC}"
echo -e "${BLUE}   Description: $DESCRIPTION${NC}"
echo ""

FILES_TO_PATCH=()

# Check for non-interactive mode (AI agent mode)
if [ -n "$PATCH_NO_PROMPT" ] && [ -n "$PATCH_FILES" ]; then
    echo -e "${BLUE}🤖 AI Agent Mode: Using predefined files${NC}"
    IFS=',' read -ra FILES_TO_PATCH <<< "$PATCH_FILES"
    for i in "${!FILES_TO_PATCH[@]}"; do
        FILES_TO_PATCH[$i]=$(echo "${FILES_TO_PATCH[$i]}" | xargs)
    done
    echo -e "${GREEN}   Files: ${FILES_TO_PATCH[*]}${NC}"
else
    # Interactive file selection
    echo -e "${YELLOW}Select files to include in patch:${NC}"
    echo ""
    echo "1. Select files manually"
    echo "2. Use git diff (unstaged changes)"
    echo "3. Use git diff (staged changes)"
    echo "4. Specific file paths (comma-separated)"
    echo ""
    read -p "Choice (1-4): " CHOICE

    case $CHOICE in
        1)
            echo -e "\n${BLUE}Available Python files with recent changes:${NC}"
            find app -name "*.py" -mtime -7 -type f | nl
            echo ""
            read -p "Enter file numbers (space-separated, e.g. 1 3 5): " FILE_NUMS
            for NUM in $FILE_NUMS; do
                FILE=$(find app -name "*.py" -mtime -7 -type f | sed -n "${NUM}p")
                if [ -n "$FILE" ]; then
                    FILES_TO_PATCH+=("$FILE")
                fi
            done
            ;;
        2)
            echo -e "\n${BLUE}Git unstaged changes:${NC}"
            if git rev-parse --git-dir > /dev/null 2>&1; then
                FILES_TO_PATCH=($(git diff --name-only))
            else
                echo -e "${RED}Not a git repository${NC}"
                exit 1
            fi
            ;;
        3)
            echo -e "\n${BLUE}Git staged changes:${NC}"
            if git rev-parse --git-dir > /dev/null 2>&1; then
                FILES_TO_PATCH=($(git diff --cached --name-only))
            else
                echo -e "${RED}Not a git repository${NC}"
                exit 1
            fi
            ;;
        4)
            echo ""
            read -p "Enter file paths (comma-separated): " FILE_INPUT
            IFS=',' read -ra FILES_TO_PATCH <<< "$FILE_INPUT"
            # Trim whitespace
            for i in "${!FILES_TO_PATCH[@]}"; do
                FILES_TO_PATCH[$i]=$(echo "${FILES_TO_PATCH[$i]}" | xargs)
            done
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
fi

# Copy files
if [ ${#FILES_TO_PATCH[@]} -eq 0 ]; then
    echo -e "${RED}No files selected${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}📁 Copying files to patch:${NC}"
for FILE in "${FILES_TO_PATCH[@]}"; do
    if [ -f "$FILE" ]; then
        # Preserve directory structure
        DEST_DIR="$PATCH_DIR/files/$(dirname "$FILE")"
        mkdir -p "$DEST_DIR"
        cp "$FILE" "$DEST_DIR/"
        echo -e "${GREEN}   ✅ $FILE${NC}"
    else
        echo -e "${RED}   ❌ File not found: $FILE${NC}"
    fi
done

# Ask for SQL migration
echo ""
if [ -n "$PATCH_NO_PROMPT" ] && [ -n "$PATCH_MIGRATION" ]; then
    echo -e "${BLUE}🤖 AI Agent Mode: Using predefined migration${NC}"
    echo "$PATCH_MIGRATION" > "$PATCH_DIR/migrations/001_${VERSION_TAG}.sql"
    echo -e "${GREEN}   ✅ Migration script created${NC}"
elif [ -z "$PATCH_NO_PROMPT" ]; then
    read -p "Include SQL migration? (y/n): " ADD_MIGRATION
    if [[ $ADD_MIGRATION =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}Enter SQL migration (end with Ctrl+D):${NC}"
        cat > "$PATCH_DIR/migrations/001_${VERSION_TAG}.sql"
        if [ -s "$PATCH_DIR/migrations/001_${VERSION_TAG}.sql" ]; then
            echo -e "${GREEN}   ✅ Migration script created${NC}"
        else
            rm "$PATCH_DIR/migrations/001_${VERSION_TAG}.sql"
        fi
    fi
fi

# Ask for pre-install script
echo ""
if [ -z "$PATCH_NO_PROMPT" ]; then
    read -p "Include pre-install script? (y/n): " ADD_PRE
    if [[ $ADD_PRE =~ ^[Yy]$ ]]; then
        cat > "$PATCH_DIR/pre_install.sh" << 'EOF'
#!/bin/bash
# Pre-install script - runs BEFORE files are copied
set -e

echo "🔧 Running pre-install checks..."

# Add your pre-install commands here
# Example: Check if backend is running
# if ! pgrep -f "uvicorn main:app" > /dev/null; then
#     echo "❌ Backend not running"
#     exit 1
# fi

echo "✅ Pre-install checks passed"
EOF
        chmod +x "$PATCH_DIR/pre_install.sh"
        echo -e "${GREEN}   ✅ Pre-install script created (edit if needed)${NC}"
    fi
fi

# Ask for post-install script
echo ""
if [ -z "$PATCH_NO_PROMPT" ]; then
    read -p "Include post-install script? (y/n): " ADD_POST
    if [[ $ADD_POST =~ ^[Yy]$ ]]; then
        cat > "$PATCH_DIR/post_install.sh" << 'EOF'
#!/bin/bash
# Post-install script - runs AFTER files are copied
set -e

echo "🔄 Running post-install tasks..."

# Restart backend
echo "   Restarting backend..."
./restart_backend.sh

# Optional: Rebuild frontend
# echo "   Rebuilding frontend..."
# cd frontend && npm run build && cd ..

# Optional: Restart nginx
# echo "   Restarting nginx..."
# sudo systemctl restart nginx

echo "✅ Post-install complete"
EOF
        chmod +x "$PATCH_DIR/post_install.sh"
        echo -e "${GREEN}   ✅ Post-install script created (edit if needed)${NC}"
    fi
elif [ -n "$PATCH_NO_PROMPT" ]; then
    # AI Agent mode: Always create post-install with backend restart
    cat > "$PATCH_DIR/post_install.sh" << 'EOF'
#!/bin/bash
set -e
echo "🔄 Restarting backend..."
cd /opt/liara && ./restart_backend.sh
echo "✅ Post-install complete"
EOF
    chmod +x "$PATCH_DIR/post_install.sh"
    echo -e "${GREEN}   ✅ Auto-generated post-install script (backend restart)${NC}"
fi

# Create rollback script
cat > "$PATCH_DIR/rollback.sh" << EOF
#!/bin/bash
# Rollback script for patch ${VERSION_TAG}
set -e

echo "⚠️  Rolling back patch ${VERSION_TAG}..."

# Restore from the backup created for this patch (pre_${VERSION_TAG}).
# Falls back to the newest backup only if no matching one exists.
MATCHING_BACKUP=\$(ls -t backups/ 2>/dev/null | grep -- "_pre_${VERSION_TAG}\$" | head -1)
if [ -n "\$MATCHING_BACKUP" ]; then
    LATEST_BACKUP="\$MATCHING_BACKUP"
else
    echo "⚠️  No backup tagged 'pre_${VERSION_TAG}' found, falling back to newest backup"
    LATEST_BACKUP=\$(ls -t backups/ 2>/dev/null | head -1)
fi
if [ -z "\$LATEST_BACKUP" ]; then
    echo "❌ No backup found!"
    exit 1
fi

echo "📦 Restoring from backup: \$LATEST_BACKUP"

# Restore files
for FILE in ${FILES_TO_PATCH[@]}; do
    if [ -f "backups/\$LATEST_BACKUP/\$FILE" ]; then
        cp "backups/\$LATEST_BACKUP/\$FILE" "\$FILE"
        echo "   ✅ Restored \$FILE"
    fi
done

# Restart services
echo "🔄 Restarting services..."
./restart_backend.sh

echo "✅ Rollback complete"
EOF
chmod +x "$PATCH_DIR/rollback.sh"

# Create patch info
cat > "$PATCH_DIR/PATCH_INFO.txt" << EOF
Liara Patch
===========
Version: $VERSION_TAG
Created: $(date)
Description: $DESCRIPTION

Files Included:
---------------
$(for FILE in "${FILES_TO_PATCH[@]}"; do echo "- $FILE"; done)

Migrations:
-----------
$(if [ -f "$PATCH_DIR/migrations/001_${VERSION_TAG}.sql" ]; then echo "✓ 001_${VERSION_TAG}.sql"; else echo "None"; fi)

Scripts:
--------
$(if [ -f "$PATCH_DIR/pre_install.sh" ]; then echo "✓ pre_install.sh"; else echo "✗ pre_install.sh"; fi)
$(if [ -f "$PATCH_DIR/post_install.sh" ]; then echo "✓ post_install.sh"; else echo "✗ post_install.sh"; fi)
✓ rollback.sh

Installation Instructions:
--------------------------
1. Create backup: ./create_backup.sh pre_${VERSION_TAG}
2. Apply patch: ./apply_patch.sh patches/${TIMESTAMP}_${VERSION_TAG}.tar.gz
3. Test the changes
4. If issues: cd patches/${TIMESTAMP}_${VERSION_TAG} && ./rollback.sh

Manual Installation:
--------------------
1. Backup current system
2. cd patches/${TIMESTAMP}_${VERSION_TAG}
3. Run pre_install.sh (if exists)
4. Copy files: cp -r files/* /opt/liara/
5. Apply migrations: sudo -u postgres psql liara_db < migrations/001_${VERSION_TAG}.sql
6. Run post_install.sh (if exists)
7. Test the system

Rollback:
---------
cd patches/${TIMESTAMP}_${VERSION_TAG} && ./rollback.sh

Notes:
------
- Always create a backup before applying patches
- Test in a staging environment first if possible
- Check logs after installation: tail -f /tmp/liara_backend.log
EOF

# Create tarball
echo ""
if [ -n "$PATCH_NO_PROMPT" ]; then
    # AI Agent mode: Always create tarball
    echo -e "${BLUE}📦 Creating tarball (AI mode)...${NC}"
    cd patches
    tar -czf "${TIMESTAMP}_${VERSION_TAG}.tar.gz" "${TIMESTAMP}_${VERSION_TAG}"
    TAR_SIZE=$(du -sh "${TIMESTAMP}_${VERSION_TAG}.tar.gz" | cut -f1)
    cd ..
    echo -e "${GREEN}   ✅ Tarball: patches/${TIMESTAMP}_${VERSION_TAG}.tar.gz ($TAR_SIZE)${NC}"
else
    read -p "Create tarball? (y/n): " CREATE_TAR
    if [[ $CREATE_TAR =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}📦 Creating tarball...${NC}"
        cd patches
        tar -czf "${TIMESTAMP}_${VERSION_TAG}.tar.gz" "${TIMESTAMP}_${VERSION_TAG}"
        TAR_SIZE=$(du -sh "${TIMESTAMP}_${VERSION_TAG}.tar.gz" | cut -f1)
        cd ..
        echo -e "${GREEN}   ✅ Tarball created: patches/${TIMESTAMP}_${VERSION_TAG}.tar.gz ($TAR_SIZE)${NC}"
    fi
fi

# Summary
PATCH_SIZE=$(du -sh "$PATCH_DIR" | cut -f1)
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Patch Created! ✅                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Location:${NC} $PATCH_DIR"
echo -e "  ${BLUE}Size:${NC}     $PATCH_SIZE"
echo -e "  ${BLUE}Files:${NC}    ${#FILES_TO_PATCH[@]}"
echo ""
echo -e "${BLUE}📂 Patch Contents:${NC}"
ls -lh "$PATCH_DIR" | tail -n +2
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review patch: cat $PATCH_DIR/PATCH_INFO.txt"
echo -e "  2. Create backup: ./create_backup.sh pre_${VERSION_TAG}"
echo -e "  3. Apply patch: ./apply_patch.sh patches/${TIMESTAMP}_${VERSION_TAG}.tar.gz"
echo ""
