# 🔐 Liara - Login-Informationen

## Aktualisiert: 3. Dezember 2025

### ✅ Aktive Benutzerkonten

| Username   | Passwort  | Rolle  | E-Mail               |
|------------|-----------|--------|----------------------|
| `admin`    | `admin123`| Admin  | admin@example.com    |
| `demouser` | `demo123` | User   | demo@example.com     |
| `testuser` | `test123` | User   | test@example.com     |

---

## 📝 Wichtige Hinweise

### ⚠️ Passwort-Migration durchgeführt
- **Alte Passwörter ungültig!** (waren mit bcrypt gehasht)
- **Neue Passwörter** nutzen Argon2id (sicherer)
- Alle Passwörter wurden am 3.12.2025 zurückgesetzt

### 🔤 Benutzernamen sind Case-Insensitive
Die folgenden Varianten funktionieren alle:
- `admin` = `Admin` = `ADMIN` = `AdMiN` ✅
- `demouser` = `DemoUser` = `DEMOUSER` ✅

### 🔒 Sicherheitsverbesserungen
- ✅ Argon2id Passwort-Hashing (GPU-resistent)
- ✅ Refresh Tokens (30 Tage)
- ✅ Access Tokens (60 Minuten)
- ✅ Token-Rotation bei jedem Refresh
- ✅ SECRET_KEY in .env (nicht mehr hardcoded)

---

## 🚀 Erste Schritte

1. **Login**: https://liara.mw-dresden.myfritz.link
2. **Benutzername**: `admin` (oder ADMIN, Admin, etc.)
3. **Passwort**: `admin123`
4. **Hard Refresh**: Strg+Shift+R (oder Cmd+Shift+R auf Mac)

### Alternative: Gast-Modus
- Klicke auf "👋 Als Gast reinschauen"
- Keine Registrierung nötig
- Limitiert: 10 Nachrichten, keine Funktionen wie Tasks/Kalender

---

## 🔧 Passwort ändern (später)

Nutze die Config-Seite oder API:
```bash
curl -X PATCH http://localhost:8100/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password":"neues_passwort"}'
```

---

## ⚠️ WICHTIG für Produktion

Diese Passwörter sind **nur für Entwicklung/Testing**!

Für Produktiv-Umgebung:
1. Ändere alle Passwörter
2. Verwende starke Passwörter (min. 12 Zeichen)
3. Aktiviere 2FA (später implementieren)
4. Rotiere SECRET_KEY regelmäßig

---

## 📞 Support

Bei Login-Problemen:
1. Hard Refresh im Browser (Strg+Shift+R)
2. Browser-Cache leeren
3. Developer Console öffnen (F12) → Network tab prüfen
4. Backend-Logs prüfen: `tail -f /tmp/liara_backend.log`
