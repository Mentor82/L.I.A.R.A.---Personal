# Liara Theme System v1.0

## Übersicht

Das Liara Theme System ist ein zentralisiertes CSS-Variablen-basiertes Design-System, das konsistentes Theming über alle Komponenten hinweg ermöglicht und automatisches Light/Dark-Mode Switching unterstützt.

## Features

✅ **Automatisches Theme-Switching**: Dark/Light-Mode mit einem Toggle
✅ **Semantische Variablen**: Bedeutungsvolle Namen wie `--bg-hover`, `--bg-danger-subtle`
✅ **Konsistente Alpha-Werte**: Standardisierte Transparenzen für alle Komponenten
✅ **Responsive Design**: Clamp-basierte Werte für Spacing und Typography
✅ **85% Migration**: Über 200 hardcodierte rgba() Werte durch CSS-Variablen ersetzt

## Architektur

```
frontend/src/styles/
├── theme.css               # Zentrale Theme-Definition (Dark + Light)
├── theme-utilities.css     # Wiederverwendbare CSS-Klassen
├── components.css          # Globale Component Styles
└── modern-design.css       # Design System Extensions
```

## CSS-Variablen

### Basis-Farben

```css
/* Dark Mode (Standard) */
:root {
  --color-bg: #0C111B;              /* Haupthintergrund */
  --color-bg-alt: #0F1E35;          /* Sekundärer Hintergrund */
  --color-bg-tertiary: #141c2e;     /* Tertiärer Hintergrund */
  --color-border: rgba(255, 255, 255, 0.06);
  
  --color-text: #E2E8F0;
  --color-text-muted: #94A3B8;
  
  --color-primary: #38BDF8;          /* Cyan/Blue */
  --color-purple: #9F7AEA;
  --color-cyan: #00D9FF;
  
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-danger: #EF4444;
  --color-info: #3B82F6;
}

/* Light Mode */
:root[data-theme="light"] {
  --color-bg: #F0F4F8;
  --color-bg-alt: #FFFFFF;
  --color-bg-tertiary: #E5EAF0;
  --color-border: rgba(0, 0, 0, 0.1);
  
  --color-text: #1A202C;
  --color-text-muted: #4A5568;
  
  /* Primärfarben bleiben gleich */
}
```

### Semantische Backgrounds

#### Neutrale Hintergründe
```css
--bg-subtle      /* rgba(255, 255, 255, 0.02) in dark, rgba(0,0,0,0.02) in light */
--bg-muted       /* rgba(255, 255, 255, 0.03) in dark */
--bg-card        /* rgba(255, 255, 255, 0.05) in dark */
--bg-hover       /* rgba(255, 255, 255, 0.05) in dark */
--bg-active      /* rgba(255, 255, 255, 0.08) in dark */
```

#### Input/Form Hintergründe
```css
--bg-input       /* rgba(0, 0, 0, 0.2) in dark, rgba(0,0,0,0.05) in light */
--bg-input-hover /* rgba(0, 0, 0, 0.3) in dark */
--bg-dropdown    /* rgba(0, 0, 0, 0.4) in dark */
```

#### Overlay Hintergründe
```css
--overlay-light  /* rgba(0, 0, 0, 0.3) in dark, rgba(255,255,255,0.6) in light */
--overlay-medium /* rgba(0, 0, 0, 0.5) in dark, rgba(255,255,255,0.8) in light */
--overlay-dark   /* rgba(0, 0, 0, 0.7) in dark, rgba(255,255,255,0.95) in light */
```

#### Akzent Hintergründe
```css
/* Primary (Cyan/Blue) */
--bg-primary-subtle  /* rgba(56, 189, 248, 0.08) */
--bg-primary-muted   /* rgba(56, 189, 248, 0.1) */
--bg-primary-hover   /* rgba(56, 189, 248, 0.15) */

/* Purple */
--bg-purple-subtle   /* rgba(139, 92, 246, 0.1) */
--bg-purple-muted    /* rgba(139, 92, 246, 0.15) */
--bg-purple-hover    /* rgba(139, 92, 246, 0.2) */

/* Cyan */
--bg-cyan-subtle     /* rgba(0, 247, 255, 0.05) */
--bg-cyan-muted      /* rgba(0, 247, 255, 0.1) */
--bg-cyan-hover      /* rgba(0, 247, 255, 0.15) */

/* Status Colors */
--bg-success-subtle  /* rgba(16, 185, 129, 0.1) */
--bg-success-muted   /* rgba(16, 185, 129, 0.15) */

--bg-warning-subtle  /* rgba(245, 158, 11, 0.1) */
--bg-warning-muted   /* rgba(245, 158, 11, 0.15) */

--bg-danger-subtle   /* rgba(239, 68, 68, 0.1) */
--bg-danger-muted    /* rgba(239, 68, 68, 0.2) */
```

### Typography & Spacing

```css
/* Responsive Typography */
--text-xs: clamp(10px, 0.7vw, 12px);
--text-sm: clamp(12px, 0.85vw, 14px);
--text-base: clamp(14px, 0.95vw, 16px);
--text-lg: clamp(16px, 1.2vw, 20px);
--text-xl: clamp(20px, 1.5vw, 26px);
--text-2xl: clamp(24px, 1.8vw, 32px);

/* Responsive Spacing */
--space-xs: clamp(2px, 0.25vw, 4px);
--space-sm: clamp(4px, 0.5vw, 8px);
--space-md: clamp(6px, 0.75vw, 12px);
--space-lg: clamp(8px, 1vw, 16px);
--space-xl: clamp(12px, 1.5vw, 24px);

/* Border Radius */
--radius-sm: clamp(4px, 0.4vw, 6px);
--radius-md: clamp(8px, 0.8vw, 12px);
--radius-lg: clamp(12px, 1.2vw, 18px);
```

## Utility-Klassen

### Background Utilities

```html
<!-- Neutrale Backgrounds -->
<div class="bg-subtle">Sehr subtiler Hintergrund</div>
<div class="bg-muted">Gedämpfter Hintergrund</div>
<div class="bg-card">Karten-Hintergrund</div>
<div class="bg-hover">Hover-Zustand</div>

<!-- Akzent Backgrounds -->
<div class="bg-primary-subtle">Primary subtle</div>
<div class="bg-purple-muted">Purple muted</div>
<div class="bg-danger-subtle">Danger subtle</div>

<!-- Input Backgrounds -->
<input class="bg-input" />
<div class="bg-dropdown">Dropdown-Menü</div>

<!-- Overlays -->
<div class="overlay-dark">Dunkles Overlay</div>
```

### Component Utilities

```html
<!-- Card -->
<div class="card-bg">
  Auto-theme-aware Karte mit Border und Hover-Effekt
</div>

<!-- Input -->
<input class="input-bg" placeholder="Auto-styled input" />

<!-- Button -->
<button class="btn-subtle">Subtiler Button</button>

<!-- Modal -->
<div class="modal-overlay">
  <div class="modal-content">
    Auto-styled Modal
  </div>
</div>

<!-- Dropdown -->
<div class="dropdown-menu">
  <div class="dropdown-item">Item 1</div>
  <div class="dropdown-item">Item 2</div>
</div>
```

### Theme-Aware Utilities

```html
<!-- Auto-adjust für Light/Dark -->
<div class="theme-surface">Passt sich automatisch an</div>
<p class="theme-text">Text in korrekter Farbe</p>
<p class="theme-text-muted">Gedämpfter Text</p>
```

## Migration von alten Styles

### Vorher (Hardcodiert)
```css
.my-component {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #E2E8F0;
}

.my-component:hover {
  background: rgba(255, 255, 255, 0.08);
}
```

### Nachher (Theme-Variablen)
```css
.my-component {
  background: var(--bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.my-component:hover {
  background: var(--bg-hover);
}
```

### Oder mit Utility-Klassen
```html
<div class="card-bg theme-text">
  Automatisch theme-aware
</div>
```

## Light/Dark Mode Toggle

### Implementierung

```jsx
// ThemeToggle.jsx
const [theme, setTheme] = useState(
  localStorage.getItem('liara_theme') || 'dark'
);

const toggleTheme = () => {
  const newTheme = theme === 'dark' ? 'light' : 'dark';
  setTheme(newTheme);
  localStorage.setItem('liara_theme', newTheme);
  document.documentElement.setAttribute('data-theme', newTheme);
};

// Beim Init
useEffect(() => {
  document.documentElement.setAttribute('data-theme', theme);
}, []);
```

### Toggle-Button
```html
<button onClick={toggleTheme}>
  {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
</button>
```

## Best Practices

### ✅ DO

1. **Verwende semantische Variablen**
   ```css
   background: var(--bg-card);
   ```

2. **Nutze Utility-Klassen für einfache Styles**
   ```html
   <div class="bg-hover theme-text">...</div>
   ```

3. **Verwende Theme-Variables für Borders**
   ```css
   border: 1px solid var(--color-border);
   ```

4. **Responsive Spacing mit CSS-Variablen**
   ```css
   padding: var(--space-md);
   gap: var(--space-sm);
   ```

### ❌ DON'T

1. **Keine hardcodierten rgba() Werte**
   ```css
   /* ❌ Schlecht */
   background: rgba(255, 255, 255, 0.05);
   
   /* ✅ Gut */
   background: var(--bg-card);
   ```

2. **Keine fixed Hex-Farben für Backgrounds**
   ```css
   /* ❌ Schlecht */
   background: #1e1e2e;
   
   /* ✅ Gut */
   background: var(--color-bg-tertiary);
   ```

3. **Keine Theme-spezifischen Klassen**
   ```css
   /* ❌ Schlecht */
   .dark-mode-card { background: #1e1e2e; }
   .light-mode-card { background: #fff; }
   
   /* ✅ Gut */
   .card { background: var(--color-bg-alt); }
   ```

## Migration-Scripts

### Automatische Migration bestehender CSS-Dateien

```bash
# Haupt-Migration
cd /opt/liara/frontend
./migrate-theme.sh

# Verbleibende spezifische Werte
cd /opt/liara/frontend/src
./migrate-remaining.sh
```

### Manuelle Migration-Checks

```bash
# Finde verbleibende hardcodierte Werte
grep -r "background: rgba" --include="*.css" | grep -v "var(--"

# Finde hardcodierte Hex-Colors
grep -r "background: #" --include="*.css" | grep -v "var(--"
```

## Performance

- **CSS-Variablen**: Keine zusätzliche Build-Zeit, native Browser-Support
- **Clamp()**: Smooth responsive scaling ohne Media Queries
- **Theme-Switching**: Instant Update ohne Page-Reload (nur CSS-Variable Änderung)

## Browser-Support

- ✅ Chrome/Edge 88+
- ✅ Firefox 85+
- ✅ Safari 14+
- ✅ Mobile Browsers (iOS 14+, Android 88+)

## Weitere Entwicklung

### Geplante Features

- [ ] Automatischer System-Theme-Detection (`prefers-color-scheme`)
- [ ] High-Contrast Mode Support
- [ ] Theme-Preset System (Ocean, Forest, Sunset, etc.)
- [ ] Accessibility-Mode (höhere Kontraste)
- [ ] Animation-Preferences (`prefers-reduced-motion`)

### Erweiterung der Variablen

Neue Variablen können einfach hinzugefügt werden:

```css
/* In theme.css */
:root {
  /* ... existing variables ... */
  --bg-neue-farbe: rgba(123, 45, 67, 0.1);
}

:root[data-theme="light"] {
  --bg-neue-farbe: rgba(123, 45, 67, 0.2);
}
```

## Troubleshooting

### Theme wechselt nicht

1. Prüfe ob `data-theme` Attribut gesetzt ist:
   ```js
   console.log(document.documentElement.getAttribute('data-theme'));
   ```

2. Stelle sicher dass `theme.css` importiert ist:
   ```css
   /* index.css */
   @import './styles/theme.css';
   ```

### Farben sehen falsch aus

1. Prüfe ob CSS-Variablen geladen sind:
   ```js
   getComputedStyle(document.documentElement).getPropertyValue('--color-bg');
   ```

2. Überprüfe Specificity-Probleme (CSS-Variablen haben niedrige Specificity)

### Build-Fehler

```bash
# CSS-Syntax prüfen
npm run build 2>&1 | grep -i error

# Fehlende Imports
grep -r "@import" frontend/src --include="*.css"
```

---

**Version**: 1.0  
**Datum**: 6. Dezember 2025  
**Migration Status**: 85% Complete (200+ rgba() → CSS-Variables)
