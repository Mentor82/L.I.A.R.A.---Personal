#!/bin/bash

# LIARA Theme Migration Script
# Ersetzt hardcodierte Farben mit CSS-Variablen

echo "🎨 Starting theme migration..."

# Backup erstellen
BACKUP_DIR="/opt/liara/frontend/backups/theme_migration_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "📦 Creating backup in $BACKUP_DIR..."
cp -r /opt/liara/frontend/src /opt/liara/frontend/src/components "$BACKUP_DIR/"

# CSS-Dateien finden
CSS_FILES=$(find /opt/liara/frontend/src -name "*.css" -not -path "*/backups/*" -not -path "*/node_modules/*")

echo "🔄 Processing CSS files..."

for file in $CSS_FILES; do
  echo "  Processing: $(basename $file)"
  
  # Component Backgrounds
  sed -i 's/background: rgba(255, 255, 255, 0\.02)/background: var(--bg-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.03)/background: var(--bg-muted)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.05)/background: var(--bg-card)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.08)/background: var(--bg-active)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.1)/background: var(--bg-hover)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.12)/background: var(--bg-active)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.15)/background: var(--bg-active)/g' "$file"
  sed -i 's/background: rgba(255, 255, 255, 0\.2)/background: var(--bg-active)/g' "$file"
  
  # Input Backgrounds
  sed -i 's/background: rgba(0, 0, 0, 0\.2)/background: var(--bg-input)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.3)/background: var(--bg-input-hover)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.4)/background: var(--bg-dropdown)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.5)/background: var(--overlay-medium)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.6)/background: var(--overlay-medium)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.7)/background: var(--overlay-dark)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.95)/background: var(--overlay-dark)/g' "$file"
  
  # Primary/Cyan Backgrounds
  sed -i 's/background: rgba(56, 189, 248, 0\.08)/background: var(--bg-primary-subtle)/g' "$file"
  sed -i 's/background: rgba(56, 189, 248, 0\.1)/background: var(--bg-primary-muted)/g' "$file"
  sed -i 's/background: rgba(56, 189, 248, 0\.15)/background: var(--bg-primary-hover)/g' "$file"
  sed -i 's/background: rgba(56, 189, 248, 0\.2)/background: var(--bg-primary-hover)/g' "$file"
  
  sed -i 's/background: rgba(0, 247, 255, 0\.05)/background: var(--bg-cyan-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 247, 255, 0\.1)/background: var(--bg-cyan-muted)/g' "$file"
  sed -i 's/background: rgba(0, 247, 255, 0\.15)/background: var(--bg-cyan-hover)/g' "$file"
  sed -i 's/background: rgba(0, 247, 255, 0\.2)/background: var(--bg-cyan-hover)/g' "$file"
  sed -i 's/background: rgba(0, 247, 255, 0\.3)/background: var(--bg-cyan-hover)/g' "$file"
  
  sed -i 's/background: rgba(0, 217, 255, 0\.02)/background: var(--bg-cyan-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 217, 255, 0\.03)/background: var(--bg-cyan-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 217, 255, 0\.05)/background: var(--bg-cyan-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 217, 255, 0\.1)/background: var(--bg-cyan-muted)/g' "$file"
  sed -i 's/background: rgba(0, 217, 255, 0\.2)/background: var(--bg-cyan-hover)/g' "$file"
  
  # Purple Backgrounds
  sed -i 's/background: rgba(139, 92, 246, 0\.05)/background: var(--bg-purple-subtle)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.1)/background: var(--bg-purple-subtle)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.12)/background: var(--bg-purple-muted)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.15)/background: var(--bg-purple-muted)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.18)/background: var(--bg-purple-muted)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.2)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.3)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.35)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.4)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.5)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(139, 92, 246, 0\.7)/background: var(--bg-purple-hover)/g' "$file"
  
  sed -i 's/background: rgba(102, 126, 234, 0\.1)/background: var(--bg-purple-subtle)/g' "$file"
  sed -i 's/background: rgba(102, 126, 234, 0\.2)/background: var(--bg-purple-hover)/g' "$file"
  sed -i 's/background: rgba(102, 126, 234, 0\.3)/background: var(--bg-purple-hover)/g' "$file"
  
  # Success Backgrounds
  sed -i 's/background: rgba(16, 185, 129, 0\.1)/background: var(--bg-success-subtle)/g' "$file"
  sed -i 's/background: rgba(16, 185, 129, 0\.15)/background: var(--bg-success-muted)/g' "$file"
  sed -i 's/background: rgba(16, 185, 129, 0\.2)/background: var(--bg-success-muted)/g' "$file"
  
  sed -i 's/background: rgba(34, 197, 94, 0\.15)/background: var(--bg-success-subtle)/g' "$file"
  sed -i 's/background: rgba(34, 197, 94, 0\.2)/background: var(--bg-success-muted)/g' "$file"
  
  # Warning Backgrounds
  sed -i 's/background: rgba(245, 158, 11, 0\.1)/background: var(--bg-warning-subtle)/g' "$file"
  sed -i 's/background: rgba(245, 158, 11, 0\.15)/background: var(--bg-warning-muted)/g' "$file"
  sed -i 's/background: rgba(245, 158, 11, 0\.2)/background: var(--bg-warning-muted)/g' "$file"
  
  sed -i 's/background: rgba(255, 193, 7, 0\.1)/background: var(--bg-warning-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 193, 7, 0\.15)/background: var(--bg-warning-muted)/g' "$file"
  sed -i 's/background: rgba(255, 193, 7, 0\.2)/background: var(--bg-warning-muted)/g' "$file"
  
  # Danger Backgrounds
  sed -i 's/background: rgba(239, 68, 68, 0\.1)/background: var(--bg-danger-subtle)/g' "$file"
  sed -i 's/background: rgba(239, 68, 68, 0\.15)/background: var(--bg-danger-subtle)/g' "$file"
  sed -i 's/background: rgba(239, 68, 68, 0\.2)/background: var(--bg-danger-muted)/g' "$file"
  sed -i 's/background: rgba(239, 68, 68, 0\.3)/background: var(--bg-danger-muted)/g' "$file"
  sed -i 's/background: rgba(239, 68, 68, 0\.4)/background: var(--bg-danger-muted)/g' "$file"
  
  sed -i 's/background: rgba(220, 38, 38, 0\.3)/background: var(--bg-danger-muted)/g' "$file"
  
  # Border Colors
  sed -i 's/border-color: rgba(255, 255, 255, 0\.06)/border-color: var(--color-border)/g' "$file"
  sed -i 's/border-color: rgba(255, 255, 255, 0\.1)/border-color: var(--color-border)/g' "$file"
  sed -i 's/border: 1px solid rgba(255, 255, 255, 0\.06)/border: 1px solid var(--color-border)/g' "$file"
  sed -i 's/border: 1px solid rgba(255, 255, 255, 0\.1)/border: 1px solid var(--color-border)/g' "$file"
  
  sed -i 's/border-color: rgba(0, 0, 0, 0\.1)/border-color: var(--color-border)/g' "$file"
  sed -i 's/border: 1px solid rgba(0, 0, 0, 0\.1)/border: 1px solid var(--color-border)/g' "$file"
  
  # Text Colors
  sed -i 's/color: #E2E8F0/color: var(--color-text)/g' "$file"
  sed -i 's/color: #94A3B8/color: var(--color-text-muted)/g' "$file"
  
done

echo "✅ Migration complete!"
echo "📋 Backup location: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. cd /opt/liara/frontend && npm run build"
echo "2. Test dark/light mode switching"
echo "3. Review changes with: git diff src/"
