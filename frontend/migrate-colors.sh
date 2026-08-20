#!/bin/bash

# LIARA Color Migration Script
# Ersetzt hardcodierte Text- und Border-Farben mit CSS-Variablen

echo "🎨 Migrating text and border colors..."

CSS_FILES=$(find /opt/liara/frontend/src -name "*.css" -not -path "*/backups/*" -not -path "*/node_modules/*")

for file in $CSS_FILES; do
  # Text Colors - White variants
  sed -i 's/color: #fff\([^a-f0-9]\)/color: var(--color-text)\1/g' "$file"
  sed -i 's/color: #fff;/color: var(--color-text);/g' "$file"
  sed -i 's/color: #ffffff\([^a-f0-9]\)/color: var(--color-text)\1/g' "$file"
  sed -i 's/color: #ffffff;/color: var(--color-text);/g' "$file"
  sed -i 's/color: white\([^-a-z]\)/color: var(--color-text)\1/g' "$file"
  sed -i 's/color: white;/color: var(--color-text);/g' "$file"
  sed -i 's/color: rgba(255, 255, 255, 0\.8)/color: var(--color-text)/g' "$file"
  sed -i 's/color: rgba(255, 255, 255, 0\.87)/color: var(--color-text)/g' "$file"
  sed -i 's/color: rgba(255, 255, 255, 0\.9)/color: var(--color-text)/g' "$file"
  
  # Text Colors - Gray/Muted variants
  sed -i 's/color: #94a3b8/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: #94A3B8/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: #64748b/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: #64748B/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: #475569/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: #cbd5e1/color: var(--color-text-muted)/g' "$file"
  sed -i 's/color: rgba(148, 163, 184/color: var(--color-text-muted)/g' "$file"
  
  # Purple/Primary accent text
  sed -i 's/color: #a78bfa/color: var(--color-purple)/g' "$file"
  sed -i 's/color: #A78BFA/color: var(--color-purple)/g' "$file"
  sed -i 's/color: #8b5cf6/color: var(--color-purple)/g' "$file"
  sed -i 's/color: #8B5CF6/color: var(--color-purple)/g' "$file"
  sed -i 's/color: #9f7aea/color: var(--color-purple)/g' "$file"
  
  # Cyan/Primary text
  sed -i 's/color: #38bdf8/color: var(--color-primary)/g' "$file"
  sed -i 's/color: #38BDF8/color: var(--color-primary)/g' "$file"
  sed -i 's/color: #00d9ff/color: var(--color-cyan)/g' "$file"
  sed -i 's/color: #00D9FF/color: var(--color-cyan)/g' "$file"
  
  # Status colors - Success
  sed -i 's/color: #10b981/color: var(--color-success)/g' "$file"
  sed -i 's/color: #10B981/color: var(--color-success)/g' "$file"
  sed -i 's/color: #22c55e/color: var(--color-success)/g' "$file"
  
  # Status colors - Warning
  sed -i 's/color: #f59e0b/color: var(--color-warning)/g' "$file"
  sed -i 's/color: #F59E0B/color: var(--color-warning)/g' "$file"
  sed -i 's/color: #fbbf24/color: var(--color-warning)/g' "$file"
  
  # Status colors - Danger/Error
  sed -i 's/color: #ef4444/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #EF4444/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #dc2626/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #DC2626/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #fca5a5/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #FCA5A5/color: var(--color-danger)/g' "$file"
  sed -i 's/color: #f87171/color: var(--color-danger)/g' "$file"
  
  # Status colors - Info
  sed -i 's/color: #3b82f6/color: var(--color-info)/g' "$file"
  sed -i 's/color: #3B82F6/color: var(--color-info)/g' "$file"
  sed -i 's/color: #60a5fa/color: var(--color-info)/g' "$file"
  
  # Border Colors - Purple
  sed -i 's/border-color: rgba(139, 92, 246, 0\.3)/border-color: var(--color-border)/g' "$file"
  sed -i 's/border-color: rgba(139, 92, 246, 0\.5)/border-color: var(--color-purple)/g' "$file"
  sed -i 's/border-color: #8b5cf6/border-color: var(--color-purple)/g' "$file"
  sed -i 's/border-color: #8B5CF6/border-color: var(--color-purple)/g' "$file"
  
  # Border Colors - Status
  sed -i 's/border-left-color: #64748b/border-left-color: var(--color-text-muted)/g' "$file"
  sed -i 's/border-left-color: #3b82f6/border-left-color: var(--color-info)/g' "$file"
  sed -i 's/border-left-color: #f59e0b/border-left-color: var(--color-warning)/g' "$file"
  sed -i 's/border-left-color: #ef4444/border-left-color: var(--color-danger)/g' "$file"
  sed -i 's/border-left-color: #dc2626/border-left-color: var(--color-danger)/g' "$file"
  sed -i 's/border-left-color: #10b981/border-left-color: var(--color-success)/g' "$file"
  
  # Border Colors - Generic
  sed -i 's/border-color: rgba(255, 255, 255, 0\.06)/border-color: var(--color-border)/g' "$file"
  sed -i 's/border-color: rgba(255, 255, 255, 0\.1)/border-color: var(--color-border)/g' "$file"
  
done

echo "✅ Color migration complete!"
echo ""
echo "Migrated:"
echo "  - Text colors: white, gray → CSS variables"
echo "  - Accent colors: purple, cyan → CSS variables"
echo "  - Status colors: success, warning, danger, info → CSS variables"
echo "  - Border colors → CSS variables"
