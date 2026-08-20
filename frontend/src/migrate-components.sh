#!/bin/bash
# Migrate specific component colors

# Tasks.css
sed -i 's/color: #e0e0e0/color: var(--color-text)/g' components/Tasks.css
sed -i 's/color: white\([^-]\)/color: var(--color-text)\1/g' components/Tasks.css
sed -i 's/color: white;/color: var(--color-text);/g' components/Tasks.css
sed -i 's/border-color: #667eea/border-color: var(--color-purple)/g' components/Tasks.css
sed -i 's/accent-color: #667eea/accent-color: var(--color-purple)/g' components/Tasks.css
sed -i 's/color: #999/color: var(--color-text-muted)/g' components/Tasks.css
sed -i 's/background: rgba(26, 26, 46, 0\.98)/background: var(--color-bg-alt)/g' components/Tasks.css

# CalendarView.css
sed -i 's/color: white\([^-]\)/color: var(--color-text)\1/g' components/CalendarView.css
sed -i 's/color: white;/color: var(--color-text);/g' components/CalendarView.css
sed -i 's/color: #f0f0f0/color: var(--color-text)/g' components/CalendarView.css
sed -i 's/color: #667eea/color: var(--color-purple)/g' components/CalendarView.css
sed -i 's/color: #a5b4fc/color: var(--color-purple)/g' components/CalendarView.css
sed -i 's/border-color: #667eea/border-color: var(--color-purple)/g' components/CalendarView.css
sed -i 's/border-top-color: #667eea/border-top-color: var(--color-purple)/g' components/CalendarView.css

# NotesTree.css / NotesFileManager.css
sed -i 's/color: #e0e0e0/color: var(--color-text)/g' components/NotesTree.css components/NotesFileManager.css
sed -i 's/color: #c4b5fd/color: var(--color-purple)/g' components/NotesTree.css components/NotesFileManager.css
sed -i 's/color: #e9d5ff/color: var(--color-purple)/g' components/NotesTree.css components/NotesFileManager.css

echo "✅ Component-specific colors migrated"
