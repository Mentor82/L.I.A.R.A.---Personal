#!/bin/bash

# Tasks.css - Replace gradients and specific backgrounds
sed -i 's/background: linear-gradient(135deg, #8B5CF6, #EC4899)/background: var(--color-purple)/g' components/Tasks.css
sed -i 's/background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)/background: var(--color-purple)/g' components/Tasks.css
sed -i 's/background: linear-gradient(135deg, #10B981, #059669)/background: var(--color-success)/g' components/Tasks.css
sed -i 's/background: linear-gradient(135deg, rgba(139, 92, 246, 0\.15), rgba(236, 72, 153, 0\.15))/background: var(--bg-purple-muted)/g' components/Tasks.css
sed -i 's/background: linear-gradient(135deg, rgba(26, 26, 46, 0\.98) 0%, rgba(22, 33, 62, 0\.98) 100%)/background: var(--color-bg-alt)/g' components/Tasks.css
sed -i 's/background: rgba(0, 0, 0, 0\.15)/background: var(--bg-input)/g' components/Tasks.css
sed -i 's/background: rgba(255, 255, 255, 0\.06)/background: var(--bg-card)/g' components/Tasks.css
sed -i 's/background: rgba(239, 68, 68, 0\.05)/background: var(--bg-danger-subtle)/g' components/Tasks.css
sed -i 's/background: rgba(239, 68, 68, 0\.08)/background: var(--bg-danger-subtle)/g' components/Tasks.css
sed -i 's/background: rgba(102, 126, 234, 0\.15)/background: var(--bg-purple-muted)/g' components/Tasks.css

# CalendarView.css - Replace gradients
sed -i 's/background: linear-gradient(135deg, #8B5CF6, #EC4899)/background: var(--color-purple)/g' components/CalendarView.css
sed -i 's/background: linear-gradient(135deg, #667eea, #764ba2)/background: var(--color-purple)/g' components/CalendarView.css
sed -i 's/background: linear-gradient(135deg, #10B981, #059669)/background: var(--color-success)/g' components/CalendarView.css

echo "✅ Gradients replaced with solid theme colors"
