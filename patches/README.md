# Liara Patches

This directory contains patches for Liara system updates.

## Patch Workflow

### 1. Create a Patch
```bash
./create_patch.sh v2.6.2_hotfix "Fix user isolation bug"
```

Interactive options:
- Select files manually (shows recent changes)
- Use git diff (unstaged/staged)
- Specify file paths directly

The script creates:
- `patches/YYYYMMDD_HHMMSS_<version>/`
  - `files/` - Changed files with directory structure
  - `migrations/` - SQL migrations (optional)
  - `pre_install.sh` - Pre-installation checks (optional)
  - `post_install.sh` - Post-installation tasks (optional)
  - `rollback.sh` - Rollback script (automatic)
  - `PATCH_INFO.txt` - Patch documentation

### 2. Create Backup (CRITICAL!)
```bash
./create_backup.sh pre_v2.6.2_hotfix
```

### 3. Apply Patch
```bash
./apply_patch.sh patches/20251203_223000_v2.6.2_hotfix.tar.gz
```

The script will:
1. Extract patch (if tarball)
2. Show patch info
3. Confirm installation
4. Run pre-install checks
5. Apply SQL migrations
6. Copy files (with backup)
7. Run post-install tasks
8. Restart services

### 4. Rollback (if needed)
```bash
cd patches/20251203_223000_v2.6.2_hotfix
./rollback.sh
```

## Best Practices

✅ **DO:**
- Always create backup before applying patch
- Test patches in staging first
- Document changes in PATCH_INFO.txt
- Include rollback instructions
- Keep patch files small and focused

❌ **DON'T:**
- Apply patches without backup
- Mix unrelated changes in one patch
- Skip testing after installation
- Forget to restart services

## Example Use Cases

### Hotfix Single File
```bash
./create_patch.sh v2.6.2_tasks_fix "Fix tasks count isolation"
# Select: app/api/routers/tasks_router.py
# No migration, add post_install.sh for restart
```

### Database Schema Change
```bash
./create_patch.sh v2.7.0_add_visibility "Add visibility column"
# Select: app/models.py, app/api/routers/*.py
# Add migration: ALTER TABLE tasks ADD COLUMN visibility VARCHAR(20)
# Add post_install.sh for restart + frontend rebuild
```

### Config Update
```bash
./create_patch.sh v2.6.3_cors_fix "Update CORS settings"
# Select: app/main.py, app/core/config.py
# No migration, add post_install.sh
```

## Patch Naming Convention

Format: `YYYYMMDD_HHMMSS_<version>_<description>`

Examples:
- `20251203_223000_v2.6.2_hotfix`
- `20251203_230000_v2.7.0_add_visibility`
- `20251204_120000_v2.7.1_security_fix`

## Directory Structure

```
patches/
├── README.md (this file)
├── 20251203_223000_v2.6.2_hotfix/
│   ├── PATCH_INFO.txt
│   ├── files/
│   │   └── app/api/routers/tasks_router.py
│   ├── post_install.sh
│   └── rollback.sh
└── 20251203_223000_v2.6.2_hotfix.tar.gz
```
