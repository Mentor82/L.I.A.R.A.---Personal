# Admin Panel Features

## 🎯 Neu hinzugefügte Features

### 1. ⚙️ Service-Management (`/admin/services`)

**Funktionalität:**
- Echtzeit-Status aller Systemdienste
- Start/Stop/Restart/Reload Buttons für jeden Service
- Automatische Aktualisierung alle 10 Sekunden
- Docker Container Übersicht (Neo4j, Redis)

**Verwaltete Services:**
- `liara` - FastAPI Backend Server
- `liara-frontend` - Vite Development Server
- `nginx` - Web Server & Reverse Proxy
- `postgresql` - Database Server

**Sicherheit:**
- Nur für Admins zugänglich (RBAC)
- Bestätigungsdialoge vor kritischen Aktionen
- Sudo-Rechte ohne Passwort für Service-Befehle (via `/etc/sudoers.d/liara-services`)

**API Endpoints:**
```
GET  /api/admin/services/status
POST /api/admin/services/{service_name}/start
POST /api/admin/services/{service_name}/stop
POST /api/admin/services/{service_name}/restart
POST /api/admin/services/{service_name}/reload
```

### 2. 💻 SSH Terminal (`/admin/terminal`)

**Funktionalität:**
- Interaktive Shell-Befehle ausführen
- Command History (mit Pfeiltasten navigieren - geplant)
- Farbcodierte Ausgabe (Command, Output, Error, System)
- Schnellbefehle-Hilfe

**Eingebaute Befehle:**
- `clear` - Terminal leeren
- `exit` - Verbindung trennen
- `help` - Hilfe anzeigen

**Sicherheit:**
- Admin-only Zugriff
- Gesperrte destruktive Befehle: `rm`, `mkfs`, `dd`, `fdisk`, `reboot`, `shutdown`, `halt`, `poweroff`
- 30 Sekunden Timeout pro Befehl
- Alle Befehle werden protokolliert

**API Endpoints:**
```
POST /api/admin/terminal/connect
POST /api/admin/terminal/execute
```

**Beispiel-Befehle:**
```bash
# Service-Status prüfen
systemctl status liara

# Letzte Logs anzeigen
journalctl -u liara -n 20

# Docker Container
docker ps

# Speicherplatz
df -h

# System-Info
htop  # (interaktive Tools funktionieren nicht)
```

### 3. 👥 Benutzerverwaltung (verbessert)

**Neue Features:**
- Schickeres Design mit Gradient-Effekten
- Größere User-Avatare mit Glow
- Hover-Animationen
- Sticky Table Header
- Loading States mit animierten Dots

### 4. 📊 System Health (bestehend)

- CPU, Memory, Disk Usage
- Process Information
- Uptime Tracking

---

## 🔐 Sicherheitskonfiguration

### Sudoers Setup

Die Datei `/etc/sudoers.d/liara-services` erlaubt dem User `mirko` passwortloses Management der Liara-Services:

```bash
# Sudoers-Datei prüfen
sudo visudo -c

# Berechtigungen verifizieren
ls -la /etc/sudoers.d/liara-services
# Sollte: -r--r----- (0440)
```

### RBAC (Role-Based Access Control)

Alle Admin-Endpoints nutzen die `get_current_admin_user` Dependency:

```python
from core.dependencies import get_current_admin_user
from api.models.base_models import User

@router.get("/admin/services/status")
async def get_services(
    current_user: User = Depends(get_current_admin_user)
):
    # Nur für role=ADMIN
    ...
```

---

## 🚀 Deployment

### Frontend Build

```bash
cd /opt/liara/frontend
npm run build
sudo systemctl reload nginx
```

### Backend Restart

```bash
sudo systemctl restart liara
sudo systemctl status liara
```

### Logs überwachen

```bash
# Backend Logs
journalctl -u liara -f

# Frontend Logs
journalctl -u liara-frontend -f

# Nginx Logs
tail -f /var/log/nginx/error.log
```

---

## 📱 UI-Komponenten

### ServiceManagement.jsx
- Grid-Layout für Service-Cards
- Status-Badges (Aktiv/Inaktiv, Running/Stopped)
- Action Buttons mit Loading States
- Docker Section für Container

### Terminal.jsx
- Monaco-ähnliches Terminal-Design
- Command Prompt: `mirko@liara:~$`
- Farbcodierung:
  - 🔵 Blau: Commands
  - ⚪ Weiß: Output
  - 🔴 Rot: Errors
  - 🟢 Grün: System Messages

### AdminLayout.jsx
- Aktualisierte Navigation:
  - Dashboard
  - System Health
  - **Services** (NEU)
  - **Terminal** (NEU)
  - Benutzer
  - AI Models
  - System Logs

---

## 🎨 Design-System

Alle neuen Komponenten nutzen das Halo-Theme:

```css
--halo-primary: #00d9ff (Cyan)
--halo-secondary: #00ffb3 (Aqua)
--halo-accent: #00ffb3 (Green)
--halo-danger: #ff453a (Red)
--halo-warning: #ff9f0a (Orange)
```

**Effekte:**
- Gradient-Backgrounds
- Glow-Schatten auf Hover
- Smooth Transitions (cubic-bezier)
- Border-Animationen
- Loading States

---

## 🔮 Geplante Erweiterungen

### Terminal
- [ ] Command History mit ↑/↓ Navigation
- [ ] Tab-Completion
- [ ] Multi-Tab Support
- [ ] File Upload/Download
- [ ] SSH zu anderen Servern

### Service Management
- [ ] Service Logs direkt anzeigen
- [ ] Resource Usage pro Service
- [ ] Auto-Restart Konfiguration
- [ ] Service Dependencies visualisieren
- [ ] Custom Services hinzufügen

### Monitoring
- [ ] Real-time Charts
- [ ] Alert-System
- [ ] Email-Benachrichtigungen
- [ ] Performance Metrics
- [ ] Docker Stats Integration

---

## 🐛 Troubleshooting

### Services starten nicht

```bash
# Logs prüfen
journalctl -u liara -n 50

# Permissions prüfen
sudo -l | grep systemctl

# Sudoers testen
sudo systemctl status liara
```

### Terminal-Befehle funktionieren nicht

```bash
# Backend-Logs checken
journalctl -u liara -f

# Restricted Commands werden geblockt
# Siehe: RESTRICTED_COMMANDS in admin_router.py
```

### Frontend zeigt 403 Fehler

```bash
# User-Rolle prüfen
psql -U liara_user -d liara_db -c "SELECT username, role FROM users;"

# Sollte: role = 'admin' für Admin-User
```

---

## 📄 Lizenz

Teil des Liara AI Assistant Projects.
© 2025 Mirko Waldhauer
