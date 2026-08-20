# 🔄 Browser Cache leeren - Anleitung

## Problem: "Einen Moment..." bleibt hängen

Das passiert, wenn der Browser alte JavaScript-Dateien im Cache hat.

---

## ✅ Lösung: Hard Refresh

### Windows / Linux
```
Strg + Shift + R
oder
Strg + F5
```

### macOS
```
Cmd + Shift + R
oder
Cmd + Option + R
```

### Mobile (Android)
1. Chrome öffnen
2. Einstellungen (3 Punkte)
3. Datenschutz & Sicherheit
4. Browserdaten löschen
5. "Bilder und Dateien im Cache" auswählen
6. "Daten löschen"
7. Seite neu laden

### Mobile (iOS Safari)
1. Einstellungen → Safari
2. "Verlauf und Websitedaten löschen"
3. Oder: Tab schließen und neu öffnen

---

## 🛠️ Alternative: Developer Tools

### Chrome / Edge / Firefox
1. F12 drücken (Developer Tools öffnen)
2. Rechtsklick auf Reload-Button
3. "Empty Cache and Hard Reload" wählen

---

## 🔍 Prüfen ob Cache geleert wurde

1. F12 drücken
2. Network Tab öffnen
3. "Disable cache" aktivieren
4. Seite neu laden
5. Prüfen ob neue Dateien geladen werden:
   - `index-BuOrhtvC.js` (neu) ✅
   - Nicht: `index-Cjloyu_M.js` (alt) ❌

---

## 📱 Was wurde gefixt?

**Problem:** Login-API war auf `http://localhost:8100` hardcoded
**Lösung:** Jetzt nutzt es `/api` (nginx proxy)

**Vorher:**
```javascript
fetch('http://localhost:8100/auth/login')  // ❌ funktioniert nur lokal
```

**Nachher:**
```javascript
fetch('/api/auth/login')  // ✅ funktioniert über nginx proxy
```

---

## ✅ Nach Cache-Leerung sollte funktionieren:

1. Login mit `admin` / `admin123`
2. Gast-Modus Button
3. Alle API-Calls über HTTPS

---

## 🆘 Falls es immer noch nicht geht:

1. **Browser-Console öffnen** (F12 → Console)
2. **Fehlermeldungen** kopieren
3. **Network Tab** prüfen:
   - Werden requests zu `/api/auth/login` gesendet? ✅
   - Status Code 200? ✅
   - CORS-Fehler? ❌ (sollte nicht sein)

4. **Inkognito-Modus** testen (garantiert kein Cache)
