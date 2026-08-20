# 🚀 Liara Startup Guide

## Automatischer Start (empfohlen)

Liara ist als **systemd Services** konfiguriert und startet **automatisch beim Systemstart**.

### Services

```bash
# Status aller Services prüfen
sudo systemctl status liara-backend liara-sse liara-frontend

# Einzelne Status
sudo systemctl status liara-backend   # Backend API (Port 8100, 8 Workers)
sudo systemctl status liara-sse        # SSE Streaming (Port 8101, 4 Workers)
sudo systemctl status liara-frontend   # Vite Dev Server
```

---

## Service Management

### Starten

```bash
# Alle Services starten
sudo systemctl start liara-backend liara-sse liara-frontend

# Oder einzeln
sudo systemctl start liara-backend
sudo systemctl start liara-sse
sudo systemctl start liara-frontend
```

### Stoppen

```bash
# Alle Services stoppen
sudo systemctl stop liara-backend liara-sse liara-frontend

# Oder einzeln
sudo systemctl stop liara-backend
sudo systemctl stop liara-sse
```

### Neustarten

```bash
# Alle Services neustarten
sudo systemctl restart liara-backend liara-sse

# Oder einzeln
sudo systemctl restart liara-backend
sudo systemctl restart liara-sse
```

### Logs anzeigen

```bash
# Live-Logs (Backend)
sudo journalctl -u liara-backend -f

# Live-Logs (SSE)
sudo journalctl -u liara-sse -f

# Live-Logs (Frontend)
sudo journalctl -u liara-frontend -f

# Letzte 100 Zeilen
sudo journalctl -u liara-backend -n 100
```

---

## Manuelle Logs (Gunicorn/Uvicorn)

```bash
# Backend Access Logs
tail -f /var/log/liara/access.log

# Backend Error Logs
tail -f /var/log/liara/error.log
```

---

## Service-Dateien

Die systemd Service-Dateien befinden sich in:

```
/etc/systemd/system/liara-backend.service
/etc/systemd/system/liara-sse.service
/etc/systemd/system/liara-frontend.service
```

### Backend Service (`liara-backend.service`)

- **Port**: 8100
- **Workers**: 8 (Gunicorn mit UvicornWorker)
- **WorkingDirectory**: `/opt/liara/app`
- **Logs**: `/var/log/liara/access.log`, `/var/log/liara/error.log`
- **Auto-Restart**: Ja (bei Crashes)

### SSE Service (`liara-sse.service`)

- **Port**: 8101
- **Workers**: 4 (Pure Uvicorn)
- **Script**: `/opt/liara/start_sse_server.sh` (wird vom Service aufgerufen)
- **Auto-Restart**: Ja (bei Crashes)

### Frontend Service (`liara-frontend.service`)

- **Server**: Vite Dev Server
- **WorkingDirectory**: `/opt/liara/frontend`
- **Command**: `npm run dev`
- **Auto-Restart**: Ja

---

## ⚠️ WICHTIG: Alte manuelle Start-Scripts entfernt!

Die folgenden manuellen Scripts wurden **entfernt** (Konflikt mit systemd):

- ❌ `restart_backend.sh` (gelöscht - nutze `systemctl restart liara-backend`)
- ❌ `start_backend.sh` (gelöscht - nutze `systemctl start liara-backend`)
- ✅ `start_sse_server.sh` (BEHALTEN - wird vom systemd Service aufgerufen)

**Verwende ab sofort NUR systemd-Befehle für Backend/SSE Management!**

Die Scripts `restart_backend.sh` und `start_backend.sh` führten zu Port-Konflikten mit systemd.  
**Niemals manuell Gunicorn/Uvicorn starten** - nur über systemd!

---

## Autostart aktivieren/deaktivieren

### Autostart einschalten

```bash
sudo systemctl enable liara-backend
sudo systemctl enable liara-sse
sudo systemctl enable liara-frontend
```

### Autostart ausschalten

```bash
sudo systemctl disable liara-backend
sudo systemctl disable liara-sse
sudo systemctl disable liara-frontend
```

### Status prüfen

```bash
systemctl is-enabled liara-backend   # sollte "enabled" ausgeben
systemctl is-enabled liara-sse        # sollte "enabled" ausgeben
systemctl is-enabled liara-frontend   # sollte "enabled" ausgeben
```

---

## Quick Reference

| Aktion | Befehl |
|--------|--------|
| **Status prüfen** | `sudo systemctl status liara-backend liara-sse` |
| **Starten** | `sudo systemctl start liara-backend liara-sse` |
| **Stoppen** | `sudo systemctl stop liara-backend liara-sse` |
| **Neustarten** | `sudo systemctl restart liara-backend liara-sse` |
| **Logs live** | `sudo journalctl -u liara-backend -f` |
| **Service neu laden** | `sudo systemctl daemon-reload` (nach Änderungen an Service-Dateien) |

---

## Nach Code-Änderungen

```bash
# Backend/SSE Code geändert
sudo systemctl restart liara-backend liara-sse

# Frontend Code geändert (Hot-Reload aktiv, kein Neustart nötig)
# Vite überwacht Änderungen automatisch
```

---

## Troubleshooting

### Service startet nicht

```bash
# Detaillierte Logs
sudo journalctl -u liara-backend -n 100 --no-pager

# Service-Status
sudo systemctl status liara-backend

# Port bereits belegt?
lsof -i :8100
lsof -i :8101
```

### Port-Konflikte

```bash
# Alte manuelle Prozesse killen
pkill -9 -f "gunicorn main:app"
pkill -9 -f "uvicorn main:app"

# Dann Service neu starten
sudo systemctl restart liara-backend liara-sse
```

### Service-Datei geändert

```bash
# Nach Änderungen an /etc/systemd/system/liara-*.service
sudo systemctl daemon-reload
sudo systemctl restart liara-backend liara-sse
```

---

## System-Neustart

```bash
# Liara startet automatisch nach Reboot
sudo reboot
```

Nach dem Neustart sind alle Services automatisch verfügbar! 🎉

---

## Health Check

```bash
# Backend API
curl http://localhost:8100/

# SSE Server
curl http://localhost:8101/

# Frontend (Nginx)
curl http://localhost/
```

**Erwartete Ausgabe (Backend):**
```json
{
  "message": "🌙 Liara API is online and ready",
  "version": "1.0.0",
  ...
}
```

---

## Deployment

Für Produktions-Deployments siehe:
- `/opt/liara/deploy_frontend.sh` - Frontend Build + Deploy
- `/opt/liara/deploy_with_cache_clear.sh` - Deploy mit Cache-Clear
- `/opt/liara/DEPLOYMENT_GUIDE_v2.7.0.md` - Ausführliche Anleitung

---

**Letzte Aktualisierung**: 5. Dezember 2025  
**Services konfiguriert**: Backend (8 Workers), SSE (4 Workers), Frontend (Vite)
