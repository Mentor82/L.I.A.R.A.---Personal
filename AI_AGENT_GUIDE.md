# 🤖 AI Agent Guide for Liara

This guide helps AI agents (like GitHub Copilot, Claude, ChatGPT) work with Liara's patch and backup system.

---

## Quick Reference

### Create Backup
```bash
./create_backup.sh [version_tag]
```

### Create Patch (Non-Interactive Mode)
```bash
export PATCH_NO_PROMPT=1
export PATCH_FILES="app/api/routers/tasks_router.py,app/core/config.py"
export PATCH_MIGRATION="ALTER TABLE tasks ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';"
./create_patch.sh v2.7.0_add_visibility "Add visibility column to tasks"
```

### Apply Patch (Manual Mode)
```bash
# Always create backup first!
./create_backup.sh pre_v2.7.0
./apply_patch.sh patches/20251203_v2.7.0.tar.gz
```

---

## AI Agent Workflows

### 1. Hotfix Single File

**Scenario:** Fix a bug in one file

```bash
# Step 1: Create backup
./create_backup.sh pre_hotfix

# Step 2: Create patch (AI mode)
export PATCH_NO_PROMPT=1
export PATCH_FILES="app/api/routers/tasks_router.py"
./create_patch.sh v2.6.2_tasks_fix "Fix count isolation bug"

# Step 3: Apply patch
# (User must confirm interactively for safety)
./apply_patch.sh patches/TIMESTAMP_v2.6.2_tasks_fix.tar.gz
```

**What AI should tell user:**
- "I've created a patch with the fix in tasks_router.py"
- "Run `./apply_patch.sh patches/[timestamp]_v2.6.2_tasks_fix.tar.gz` to apply"
- "Backup will be created automatically if you confirm"

---

### 2. Database Migration

**Scenario:** Add new column to table

```bash
# Step 1: Backup
./create_backup.sh pre_migration

# Step 2: Create patch with SQL
export PATCH_NO_PROMPT=1
export PATCH_FILES="app/models.py,app/api/routers/tasks_router.py"
export PATCH_MIGRATION="
ALTER TABLE tasks ADD COLUMN visibility VARCHAR(20) DEFAULT 'private';
ALTER TABLE tasks ADD COLUMN shared_with INTEGER[];
CREATE INDEX idx_tasks_visibility ON tasks(visibility);
"
./create_patch.sh v2.7.0_sharing "Add sharing system"

# Patch includes:
# - Modified Python files
# - SQL migration
# - Auto-generated post_install.sh (backend restart)
```

**What AI should tell user:**
- "I've created a patch with database migration"
- "Migration adds 'visibility' and 'shared_with' columns"
- "Backend will restart automatically after applying"
- "Apply with: ./apply_patch.sh patches/[timestamp]_v2.7.0_sharing.tar.gz"

---

### 3. Config Change

**Scenario:** Update CORS settings

```bash
export PATCH_NO_PROMPT=1
export PATCH_FILES="app/main.py,app/core/config.py"
./create_patch.sh v2.6.3_cors "Update CORS for production"
```

---

## Environment Variables

### PATCH_NO_PROMPT
Set to `1` to skip all interactive prompts.

**Example:**
```bash
export PATCH_NO_PROMPT=1
```

### PATCH_FILES
Comma-separated list of files to include in patch.

**Example:**
```bash
export PATCH_FILES="app/file1.py,app/file2.py,app/core/config.py"
```

**Important:** 
- Use relative paths from `/opt/liara/`
- No spaces after commas
- Files must exist

### PATCH_MIGRATION
SQL migration script content.

**Example:**
```bash
export PATCH_MIGRATION="
ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 0;
CREATE INDEX idx_tasks_priority ON tasks(priority);
"
```

**Tips:**
- Use multi-line strings
- Include semicolons
- Test SQL separately first

---

## Output Parsing

### Patch Created Successfully

**Look for:**
```
╔════════════════════════════════════════╗
║        Patch Created! ✅                ║
╚════════════════════════════════════════╝

  Location: patches/20251203_223000_v2.7.0
  Size:     32K
  Files:    3
```

**Extract:**
- `Location` - Path to patch directory
- `Size` - Patch size
- `Files` - Number of files included

### Patch Applied Successfully

**Look for:**
```
╔════════════════════════════════════════╗
║      Patch Applied Successfully! ✅     ║
╚════════════════════════════════════════╝
```

**Next steps shown in output:**
- Check backend logs
- Test application
- Rollback command (if needed)

---

## Error Handling

### File Not Found
```
❌ File not found: app/missing.py
```

**AI should:**
- Verify file exists with `ls` or `find`
- Check path is relative to `/opt/liara/`
- Suggest correct path to user

### No Backup
```
❌ Backup required. Aborting.
```

**AI should:**
- Run `./create_backup.sh pre_[version]` first
- Then retry patch application

### Migration Fails
```
ERROR:  column "visibility" already exists
```

**AI should:**
- Check if migration was already applied
- Suggest rollback: `cd patches/[dir] && ./rollback.sh`
- Modify migration to be idempotent

---

## Best Practices for AI Agents

### ✅ DO

1. **Always suggest backup first**
   ```bash
   ./create_backup.sh pre_[feature_name]
   ```

2. **Use descriptive version tags**
   ```bash
   v2.7.0_add_sharing  # Good
   v2.7.0              # Bad (no context)
   ```

3. **Include migration context in description**
   ```bash
   ./create_patch.sh v2.7.0_visibility "Add visibility column for sharing system"
   ```

4. **Test SQL separately before including**
   ```bash
   sudo -u postgres psql liara_db -c "SELECT * FROM tasks LIMIT 1;"
   ```

5. **Tell user what files changed**
   ```
   "I've updated these files:
   - app/api/routers/tasks_router.py (fixed count bug)
   - app/models.py (added visibility column)"
   ```

### ❌ DON'T

1. **Don't skip backups**
   ```bash
   # BAD: No backup before patch
   ./apply_patch.sh patches/dangerous.tar.gz
   ```

2. **Don't mix unrelated changes**
   ```bash
   # BAD: UI + Backend + DB in one patch
   export PATCH_FILES="frontend/Tasks.css,app/api/routers/tasks_router.py"
   ```

3. **Don't use absolute paths**
   ```bash
   # BAD
   export PATCH_FILES="/opt/liara/app/main.py"
   
   # GOOD
   export PATCH_FILES="app/main.py"
   ```

4. **Don't forget to unset variables**
   ```bash
   export PATCH_NO_PROMPT=1
   ./create_patch.sh v2.7.0 "First patch"
   
   # BAD: Still in AI mode for next patch
   ./create_patch.sh v2.7.1 "Second patch"
   
   # GOOD: Unset first
   unset PATCH_NO_PROMPT PATCH_FILES PATCH_MIGRATION
   ./create_patch.sh v2.7.1 "Second patch"
   ```

5. **Don't apply patches without testing**
   ```bash
   # BAD: Apply directly to production
   ./apply_patch.sh risky_patch.tar.gz
   
   # GOOD: Test first, create backup, then apply
   ```

---

## Structured Output Examples

### Example 1: Simple Bugfix

**AI Agent Output:**
```
🔧 I've created a patch to fix the user isolation bug:

Patch: v2.6.2_isolation_fix
Files: app/api/routers/tasks_router.py
Size: 4K
Location: patches/20251203_223000_v2.6.2_isolation_fix

Changes:
- Fixed count queries to filter by user_id
- Admins see all tasks, users see only their own

To apply:
1. ./create_backup.sh pre_isolation_fix
2. ./apply_patch.sh patches/20251203_223000_v2.6.2_isolation_fix.tar.gz
3. Test with: curl -H "Authorization: Bearer $TOKEN" http://localhost:8100/tasks

Rollback (if needed):
cd patches/20251203_223000_v2.6.2_isolation_fix && ./rollback.sh
```

### Example 2: Database Migration

**AI Agent Output:**
```
🗄️ I've created a patch with database migration:

Patch: v2.7.0_add_sharing
Files: 
  - app/models.py (added visibility field)
  - app/api/routers/tasks_router.py (updated queries)
Migration: 001_v2.7.0_add_sharing.sql
  - ALTER TABLE tasks ADD COLUMN visibility VARCHAR(20)
  - ALTER TABLE tasks ADD COLUMN shared_with INTEGER[]
  - CREATE INDEX idx_tasks_visibility
Size: 12K
Location: patches/20251203_230000_v2.7.0_add_sharing

⚠️  This patch modifies the database schema!

To apply:
1. ./create_backup.sh pre_sharing_system
2. ./apply_patch.sh patches/20251203_230000_v2.7.0_add_sharing.tar.gz
3. Backend will restart automatically
4. Test sharing with: POST /tasks (with visibility field)

Rollback:
cd patches/20251203_230000_v2.7.0_add_sharing && ./rollback.sh
(Note: Database rollback requires manual intervention)
```

---

## File Structure Reference

```
/opt/liara/
├── create_backup.sh       # Backup creator
├── create_patch.sh        # Patch creator (AI-capable)
├── apply_patch.sh         # Patch applicator
├── backups/               # Backup storage
│   └── YYYYMMDD_HHMMSS_version/
│       ├── BACKUP_INFO.txt
│       ├── app/
│       ├── docs/
│       └── liara_db_dump.sql
└── patches/               # Patch storage
    ├── README.md
    └── YYYYMMDD_HHMMSS_version/
        ├── PATCH_INFO.txt
        ├── files/
        │   └── app/...
        ├── migrations/
        │   └── 001_version.sql
        ├── pre_install.sh (optional)
        ├── post_install.sh (auto-generated in AI mode)
        ├── rollback.sh (auto-generated)
        └── YYYYMMDD_HHMMSS_version.tar.gz
```

---

## Testing Patches

### Dry Run (Manual Check)

```bash
# 1. Review patch contents
cat patches/20251203_v2.7.0/PATCH_INFO.txt

# 2. Check files
ls -la patches/20251203_v2.7.0/files/

# 3. Review migration
cat patches/20251203_v2.7.0/migrations/*.sql

# 4. Check rollback script
cat patches/20251203_v2.7.0/rollback.sh
```

### Safe Testing Workflow

```bash
# 1. Backup
./create_backup.sh test_before_patch

# 2. Apply patch
./apply_patch.sh patches/test_patch.tar.gz

# 3. Test application
curl http://localhost:8100/
tail -f /tmp/liara_backend.log

# 4. If OK, keep it
echo "✅ Patch successful"

# 5. If issues, rollback
cd patches/test_patch && ./rollback.sh
```

---

## Troubleshooting

### Problem: Patch creation hangs

**Cause:** Waiting for interactive input

**Solution:**
```bash
# Ensure PATCH_NO_PROMPT is set
export PATCH_NO_PROMPT=1
```

### Problem: Files not found in patch

**Cause:** Wrong paths in PATCH_FILES

**Solution:**
```bash
# Use relative paths from /opt/liara/
export PATCH_FILES="app/main.py"  # Not /opt/liara/app/main.py
```

### Problem: Migration fails

**Cause:** Column already exists or syntax error

**Solution:**
```bash
# Test SQL first
sudo -u postgres psql liara_db << EOF
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS visibility VARCHAR(20);
EOF
```

### Problem: Backend not restarting

**Cause:** restart_backend.sh not found or not executable

**Solution:**
```bash
chmod +x /opt/liara/restart_backend.sh
./restart_backend.sh
```

---

## Advanced: Custom Post-Install

If AI agent needs custom post-install steps:

```bash
# Don't use PATCH_NO_PROMPT
# Answer 'y' to post-install script prompt
# Then edit the generated script:

vi patches/TIMESTAMP_version/post_install.sh

# Add custom commands:
#!/bin/bash
set -e
echo "🔄 Running custom post-install..."
cd /opt/liara/frontend && npm run build
sudo systemctl restart nginx
./restart_backend.sh
echo "✅ Custom post-install complete"
```

Then continue with tarball creation.

---

## Summary Commands

```bash
# AI Mode: Create patch with migration
export PATCH_NO_PROMPT=1
export PATCH_FILES="app/file1.py,app/file2.py"
export PATCH_MIGRATION="ALTER TABLE..."
./create_patch.sh v2.7.0 "Description"

# Clean up environment
unset PATCH_NO_PROMPT PATCH_FILES PATCH_MIGRATION

# Apply patch (interactive for safety)
./create_backup.sh pre_v2.7.0
./apply_patch.sh patches/TIMESTAMP_v2.7.0.tar.gz

# Check status
tail -f /tmp/liara_backend.log
curl http://localhost:8100/

# Rollback if needed
cd patches/TIMESTAMP_v2.7.0 && ./rollback.sh
```

---

**Last Updated:** 2025-12-03  
**Version:** 1.0  
**Liara Version:** 2.6.1+
