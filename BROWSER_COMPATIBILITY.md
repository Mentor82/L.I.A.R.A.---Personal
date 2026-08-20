# Browser-Kompatibilität - Liara

## ✅ Unterstützte Browser

### Desktop
- **Chrome** 90+ (April 2021)
- **Firefox** 88+ (April 2021)
- **Safari** 14+ (September 2020)
- **Edge** 90+ (April 2021)
- **Opera** 76+ (April 2021)

### Mobile
- **iOS Safari** 13+ (September 2019)
- **Chrome Android** 90+
- **Samsung Internet** 14+
- **Firefox Android** 88+

## ❌ NICHT unterstützt
- Internet Explorer 11 (EOL)
- Opera Mini (eingeschränkte JS-Unterstützung)
- Sehr alte Browser (> 2 Jahre)

## 🔧 Verwendete Features

### JavaScript (ES2020+)
- ✅ Optional Chaining (`?.`)
- ✅ Nullish Coalescing (`??`)
- ✅ Async/Await
- ✅ Promises
- ✅ Arrow Functions
- ✅ Template Literals
- ✅ Destructuring
- ✅ Spread Operator
- ✅ Modules (ESM)

### CSS
- ✅ CSS Grid
- ✅ CSS Flexbox
- ✅ CSS Custom Properties (Variables)
- ✅ CSS Animations & Transitions
- ✅ Media Queries
- ✅ Backdrop Filter (Safari 14+)
- ✅ Linear Gradients

### Web APIs
- ✅ Fetch API
- ✅ LocalStorage
- ✅ Intersection Observer
- ✅ ResizeObserver
- ✅ WebSockets (für SSE)

## 📱 Mobile Optimierungen

### Touch-Optimierung
- Min. 44px Tap-Targets (Apple HIG)
- Min. 48px Touch-Targets (Material Design)
- `font-size: 16px` verhindert iOS Auto-Zoom
- `autocomplete` Attribute für native Keyboards

### Performance
- Code-Splitting via Vite
- Lazy Loading von Komponenten
- Asset Optimization
- Gzip Compression

## 🧪 Getestet auf

- ✅ Chrome 131 (Desktop & Android)
- ✅ Firefox 133 (Desktop)
- ✅ Safari 17 (macOS & iOS)
- ✅ Edge 131 (Desktop)

## 🔍 Browser Feature Detection

Vite/React verwendet automatisch Polyfills für:
- Fehlende ES6+ Features
- CSS Autoprefixing (PostCSS)
- Legacy Browser Support (optional)

## 📊 Marktabdeckung

Mit den aktuellen Einstellungen werden ca. **95%** aller aktiven Browser unterstützt.

Ausgeschlossen:
- IE 11 (~0.3%)
- Sehr alte Mobile Browser (~1%)
- Opera Mini (~1.5%)

## 🛡️ Progressive Enhancement

Die App funktioniert ohne JavaScript nicht, da es eine SPA ist. Folgende Features sind optional:
- WebSockets (fallback zu Polling möglich)
- Notifications (graceful degradation)
- Service Worker (optional für PWA)
