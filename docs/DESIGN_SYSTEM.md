# LIARA Design System 🎨

**Zentrale Komponenten-Bibliothek für konsistentes UI-Design**

---

## Übersicht

Alle wiederverwendbaren UI-Komponenten sind in `/frontend/src/styles/components.css` definiert.  
**Einmal ändern → überall wirksam**

### Import
```css
/* Bereits in index.css importiert */
@import './styles/components.css';
```

---

## 📦 Containers & Cards

### `.page-container`
Standard-Container für Haupt-Seiten
```jsx
<div className="page-container">
  {/* Content */}
</div>
```

### `.card`
Standard Card mit Glasmorphism-Effekt
```jsx
<div className="card">
  <h3>Card Title</h3>
  <p>Card content...</p>
</div>
```

**Varianten:**
- `.card-gradient` - Mit Gradient-Hintergrund
- `.card-compact` - Kleinere Padding

---

## 📋 Headers

### `.page-header`
Haupt-Header für Seiten
```jsx
<div className="page-header">
  <div className="header-left">
    <h2>Seiten-Titel</h2>
  </div>
  <div className="header-right">
    <button className="btn-primary">Aktion</button>
  </div>
</div>
```

### `.section-header`
Section Header innerhalb von Cards
```jsx
<div className="section-header">
  <h3>Section Title</h3>
  <button className="btn-icon">⚙️</button>
</div>
```

---

## 🔘 Buttons

### `.btn-primary`
Haupt-Aktions-Button (Lila Gradient)
```jsx
<button className="btn-primary">Speichern</button>
```

### `.btn-secondary`
Alternative Aktionen (Transparent mit Border)
```jsx
<button className="btn-secondary">Abbrechen</button>
```

### `.btn-danger`
Löschen/Gefährliche Aktionen (Rot)
```jsx
<button className="btn-danger">Löschen</button>
```

### `.btn-icon`
Kleine Icon-Buttons
```jsx
<button className="btn-icon">🔄</button>
```

**Modifiers:**
- `.btn-compact` - Kleinere Variante für alle Button-Typen

---

## 📝 Forms & Inputs

### `.form-group`
Container für Label + Input
```jsx
<div className="form-group">
  <label>Benutzername</label>
  <input type="text" className="input-field" />
</div>
```

### `.input-field`
Standard Text Input
```jsx
<input type="text" className="input-field" placeholder="Text eingeben..." />
```

### `.textarea-field`
Mehrzeiliges Textfeld
```jsx
<textarea className="textarea-field" placeholder="Beschreibung..."></textarea>
```

### `.select-field`
Dropdown Select
```jsx
<select className="select-field">
  <option>Option 1</option>
  <option>Option 2</option>
</select>
```

### `.search-box` + `.search-input`
Suchfeld mit Clear-Button
```jsx
<div className="search-box">
  <input type="text" className="search-input" placeholder="Suchen..." />
  <button className="clear-search">✕</button>
</div>
```

### `.field-error`
Fehlermeldung unter Input
```jsx
<div className="form-group">
  <input type="text" className="input-field error" />
  <span className="field-error">Feld erforderlich</span>
</div>
```

---

## 🏷️ Badges & Indicators

### `.badge`
Standard Badge (Lila)
```jsx
<span className="badge">Neu</span>
```

**Varianten:**
- `.badge-success` - Grün (Erfolg)
- `.badge-warning` - Gelb (Warnung)
- `.badge-danger` - Rot (Fehler)
- `.badge-info` - Blau (Info)

```jsx
<span className="badge-success">Aktiv</span>
<span className="badge-warning">Ausstehend</span>
<span className="badge-danger">Fehler</span>
<span className="badge-info">Beta</span>
```

---

## ⏳ Loading & States

### `.spinner`
Loading Spinner
```jsx
<div className="loading-container">
  <div className="spinner"></div>
  <p>Lädt...</p>
</div>
```

### `.empty-state`
Leerer Zustand (keine Daten)
```jsx
<div className="empty-state">
  <div className="empty-state-icon">📭</div>
  <p className="empty-state-text">Keine Einträge vorhanden</p>
</div>
```

---

## 📋 Lists & Grids

### `.list-vertical`
Vertikale Liste mit Abständen
```jsx
<div className="list-vertical">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

### `.list-horizontal`
Horizontale Liste mit Wrapping
```jsx
<div className="list-horizontal">
  <span className="badge">Tag1</span>
  <span className="badge">Tag2</span>
</div>
```

### `.grid-2` / `.grid-3`
Responsive Grid Layouts
```jsx
<div className="grid-2">
  <div className="card">Item 1</div>
  <div className="card">Item 2</div>
</div>
```

---

## 📏 Dividers

### `.divider-h`
Horizontale Trennlinie
```jsx
<div className="divider-h"></div>
```

### `.divider-text`
Trennlinie mit Text
```jsx
<div className="divider-text">ODER</div>
```

---

## ✨ Animations

### Verfügbare Animationen

```jsx
<div className="animate-slide-down">Slide Down</div>
<div className="animate-fade-in">Fade In</div>
<div className="animate-slide-in-left">Slide In Left</div>
<div className="animate-scale-in">Scale In</div>
```

---

## 🛠️ Utility Classes

### Flexbox
```jsx
<div className="flex-center">Zentriert</div>
<div className="flex-between">Space Between</div>
<div className="flex-start">Start</div>
<div className="flex-column">Vertikal</div>
<div className="flex-wrap">Wrap</div>
<div className="flex-1">Flex 1</div>
```

### Gaps
```jsx
<div className="gap-xs">Extra Small Gap</div>
<div className="gap-sm">Small Gap</div>
<div className="gap-md">Medium Gap</div>
<div className="gap-lg">Large Gap</div>
<div className="gap-xl">Extra Large Gap</div>
```

### Text
```jsx
<p className="text-center">Zentriert</p>
<p className="text-left">Links</p>
<p className="text-right">Rechts</p>
<p className="text-muted">Gedämpft</p>
<p className="text-small">Klein</p>
<p className="text-large">Groß</p>
```

### Spacing
```jsx
<div className="p-0">Kein Padding</div>
<div className="p-sm">Small Padding</div>
<div className="p-md">Medium Padding</div>
<div className="p-lg">Large Padding</div>
<div className="m-auto">Margin Auto</div>
```

### Visibility
```jsx
<div className="hidden">Versteckt</div>
<div className="visible">Sichtbar</div>
```

### Overflow
```jsx
<div className="overflow-hidden">Hidden</div>
<div className="overflow-auto">Auto</div>
<div className="overflow-scroll">Scroll</div>
```

---

## 📱 Responsive Breakpoints

Alle Komponenten passen sich automatisch an:

- **Desktop**: Full Size mit `clamp()` Scaling
- **Tablet** (≤768px): Stack-Layout, volle Breite Buttons
- **Mobile** (≤480px): Single-Column Grids

---

## 🎨 Farb-System

### Primär-Farben
- **Primary**: `#8b5cf6` (Lila) - Haupt-Aktionen
- **Success**: `#22c55e` (Grün) - Erfolg
- **Warning**: `#fbbf24` (Gelb) - Warnung
- **Danger**: `#ef4444` (Rot) - Fehler
- **Info**: `#38bdf8` (Blau) - Information

### Opacity Levels
- **0.05** - Sehr subtiler Hintergrund
- **0.1** - Leichter Hintergrund
- **0.2** - Sichtbarer Hintergrund
- **0.5** - Gedämpfter Text
- **0.87** - Haupt-Text

---

## ✅ Best Practices

### ✅ DO
```jsx
// Verwende globale Komponenten
<button className="btn-primary">Speichern</button>
<div className="card">Content</div>
<input className="input-field" />
```

### ❌ DON'T
```jsx
// NICHT: Eigene Button-Styles in Component.css
.my-custom-button {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(...);
}
```

### Kombinationen
```jsx
// Globale + Lokale Classes kombinieren
<div className="card notes-specific-styling">
  {/* Card verwendet globale Styles */}
  {/* notes-specific-styling für spezifische Anpassungen */}
</div>
```

---

## 🔄 Migration Guide

### Schritt 1: Identifiziere redundante Styles
```css
/* ALT in Notes.css */
.create-button {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  /* ... */
}
```

### Schritt 2: Ersetze durch globale Klasse
```jsx
// NEU
<button className="btn-primary">Notiz erstellen</button>
```

### Schritt 3: Entferne redundanten CSS
```css
/* LÖSCHEN aus Notes.css */
/* .create-button { ... } */
```

---

## 📊 Verwendungs-Statistik

### Aktuell verwendet in:
- ✅ **Alle neuen Komponenten** (ab v3.0)
- 🔄 **Migration läuft**: Chat, Notes, Tasks, Calendar, MoodStatus, Profile

### Redundante Styles eliminiert:
- Buttons: ~15 Definitionen → 1 globale
- Cards: ~12 Definitionen → 1 globale
- Inputs: ~18 Definitionen → 1 globale
- Headers: ~10 Definitionen → 1 globale

**Gesamte Code-Reduktion**: ~500 Zeilen CSS entfernt

---

## 🚀 Neue Komponente erstellen

```jsx
// MyComponent.jsx
import './MyComponent.css'; // Nur für spezifische Styles

function MyComponent() {
  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Meine Komponente</h2>
        <button className="btn-primary">Aktion</button>
      </div>
      
      <div className="card">
        <div className="form-group">
          <label>Name</label>
          <input className="input-field" />
        </div>
        
        <div className="flex-between gap-sm">
          <button className="btn-secondary">Abbrechen</button>
          <button className="btn-primary">Speichern</button>
        </div>
      </div>
    </div>
  );
}
```

```css
/* MyComponent.css - NUR spezifische Styles */
.my-special-layout {
  /* Nur was NICHT in components.css ist */
}
```

---

## 🎯 Zusammenfassung

**Vorher**: 20+ CSS-Dateien mit identischen Button/Card/Input Styles  
**Nachher**: 1 zentrale `components.css` → überall verfügbar

**Vorteile**:
- ✅ Konsistentes Design
- ✅ Weniger Code-Duplikation
- ✅ Einfachere Wartung
- ✅ Schnellere Entwicklung
- ✅ Automatisches Responsive Design

**Bei Fragen**: Siehe `/frontend/src/styles/components.css` für alle verfügbaren Komponenten.
