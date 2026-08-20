#!/bin/bash

# Chat.css - Comprehensive color and background migration

# Text colors
sed -i 's/color: #86efac/color: var(--color-success)/g' components/Chat.css
sed -i 's/color: #c4b5fd/color: var(--color-purple)/g' components/Chat.css
sed -i 's/color: #A0AEC0/color: var(--color-text-muted)/g' components/Chat.css
sed -i 's/color: #FFC107/color: var(--color-warning)/g' components/Chat.css
sed -i 's/color: #ff5252/color: var(--color-danger)/g' components/Chat.css

# Specific backgrounds that weren't caught
sed -i 's/background: #2a2a3e/background: var(--color-bg-tertiary)/g' components/Chat.css
sed -i 's/background: white\([^-]\)/background: var(--color-bg-alt)\1/g' components/Chat.css
sed -i 's/background: white;/background: var(--color-bg-alt);/g' components/Chat.css

# Message backgrounds (if not already converted)
sed -i 's/background: rgba(34, 197, 94, 0\.15)/background: var(--bg-success-muted)/g' components/Chat.css
sed -i 's/background: rgba(244, 67, 54, 0\.2)/background: var(--bg-danger-muted)/g' components/Chat.css

echo "✅ Chat colors migrated"
