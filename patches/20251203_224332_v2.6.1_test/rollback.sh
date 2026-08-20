#!/bin/bash
# Rollback script for patch v2.6.1_test
set -e

echo "⚠️  Rolling back patch v2.6.1_test..."

# Restore from latest backup
LATEST_BACKUP=$(ls -t backups/ | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup found!"
    exit 1
fi

echo "📦 Restoring from backup: $LATEST_BACKUP"

# Restore files
for FILE in app/core/scheduler.py; do
    if [ -f "backups/$LATEST_BACKUP/$FILE" ]; then
        cp "backups/$LATEST_BACKUP/$FILE" "$FILE"
        echo "   ✅ Restored $FILE"
    fi
done

# Restart services
echo "🔄 Restarting services..."
./restart_backend.sh

echo "✅ Rollback complete"
