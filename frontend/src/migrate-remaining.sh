#!/bin/bash
# Migrate remaining specific rgba values

for file in $(find . -name "*.css"); do
  # Landing Page / PageLayout specific dark backgrounds
  sed -i 's/background: rgba(10, 14, 39, 0\.95)/background: var(--color-bg-alt)/g' "$file"
  sed -i 's/background: rgba(12, 17, 27, 0\.95)/background: var(--color-bg-alt)/g' "$file"
  sed -i 's/background: rgba(15, 30, 53, 0\.95)/background: var(--color-bg-alt)/g' "$file"
  sed -i 's/background: rgba(15, 30, 53, 0\.85)/background: var(--color-bg-alt)/g' "$file"
  sed -i 's/background: rgba(15, 30, 53, 0\.7)/background: var(--overlay-medium)/g' "$file"
  sed -i 's/background: rgba(13, 17, 23, 0\.8)/background: var(--overlay-medium)/g' "$file"
  
  # Terminal specific backgrounds
  sed -i 's/background: rgba(10, 14, 20, 0\.95)/background: var(--color-bg-alt)/g' "$file"
  sed -i 's/background: #0a0e14/background: var(--color-bg)/g' "$file"
  sed -i 's/background: #1a1a2e/background: var(--color-bg-tertiary)/g' "$file"
  sed -i 's/background: #1e1e2e/background: var(--color-bg-tertiary)/g' "$file"
  sed -i 's/background: #2a2a3e/background: var(--color-bg-tertiary)/g' "$file"
  
  # Specific alpha patterns not yet covered
  sed -i 's/background: rgba(56, 189, 248, 0\.03)/background: var(--bg-primary-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.1)/background: var(--bg-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.05)/background: var(--bg-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 0, 0, 0\.8)/background: var(--overlay-dark)/g' "$file"
  
  # Success/Warning/Danger specific colors
  sed -i 's/background: rgba(0, 255, 179, 0\.1)/background: var(--bg-success-subtle)/g' "$file"
  sed -i 's/background: rgba(0, 255, 179, 0\.15)/background: var(--bg-success-muted)/g' "$file"
  sed -i 's/background: rgba(255, 69, 58, 0\.1)/background: var(--bg-danger-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 69, 58, 0\.15)/background: var(--bg-danger-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 159, 10, 0\.05)/background: var(--bg-warning-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 159, 10, 0\.1)/background: var(--bg-warning-subtle)/g' "$file"
  sed -i 's/background: rgba(255, 152, 0, 0\.2)/background: var(--bg-warning-muted)/g' "$file"
  sed -i 's/background: rgba(251, 191, 36, 0\.2)/background: var(--bg-warning-muted)/g' "$file"
  sed -i 's/background: rgba(236, 72, 153, 0\.2)/background: var(--bg-purple-hover)/g' "$file"
  
  # Specific cyan/aqua tones
  sed -i 's/background: rgba(0, 180, 216, 0\.1)/background: var(--bg-cyan-muted)/g' "$file"
  
done

echo "✅ Remaining patterns migrated"
