# 🛠️ Setup Scripts - Installation & Konfiguration

**Version:** 1.0  
**Erstellt:** 2025-12-03  
**Ordner:** `/opt/liara/setup/`

---

## 📋 Übersicht

Dieser Ordner enthält alle Setup- und Installations-Skripte für Liara's System-Komponenten.

---

## 📁 Verfügbare Scripts

### 1. `install-ollama.sh` 🤖
**Ollama LLM Installation & Model Setup**

**Beschreibung:**
- Installiert Ollama
- Lädt alle 9 LLM-Modelle
- Konfiguriert Systemd-Service

**Verwendung:**
```bash
sudo bash /opt/liara/setup/install-ollama.sh
```

**Hinweis:** Benötigt root-Rechte

**Installierte Modelle:**
1. `llama3.2:1b` (700 MB)
2. `llama3.2:3b` (2 GB)
3. `phi3:mini` (2.3 GB)
4. `mistral:7b` (4.1 GB)
5. `deepseek-r1:7b` (4.7 GB)
6. `qwen2.5:7b` (4.7 GB)
7. `llama3.1:8b` (4.7 GB)
8. `gemma2:9b` (5.4 GB)
9. `gpt-oss:20b` (11.4 GB)

**Dauer:** ~30-45 Minuten (abhängig von Internet-Geschwindigkeit)

---

### 2. `setup-venv.sh` 🐍
**Python Virtual Environment Setup**

**Beschreibung:**
- Erstellt Python venv unter `/opt/liara/venv`
- Installiert alle Python-Dependencies
- Konfiguriert FastAPI-Backend

**Verwendung:**
```bash
bash /opt/liara/setup/setup-venv.sh
```

**Hinweis:** NICHT als root ausführen!

**Installierte Packages:**
- FastAPI + uvicorn
- SQLAlchemy + psycopg2-binary
- Alembic (Migrations)
- psutil (System-Monitoring)
- Requests (HTTP-Client)
- Pydantic (Data Validation)

**Dauer:** ~2-5 Minuten

---

## 🚀 Vollständige Installation (Reihenfolge)

### Schritt 1: System-Pakete
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
                    postgresql postgresql-contrib \
                    git curl wget
```

### Schritt 2: Python Virtual Environment
```bash
cd /opt/liara
bash setup/setup-venv.sh
```

### Schritt 3: Ollama & Modelle
```bash
sudo bash setup/install-ollama.sh
```

### Schritt 4: PostgreSQL Setup
```bash
# Datenbank erstellen
sudo -u postgres psql << EOF
CREATE DATABASE liara_db;
CREATE USER liara WITH PASSWORD 'liara_secure_2025';
GRANT ALL PRIVILEGES ON DATABASE liara_db TO liara;
\c liara_db
GRANT ALL ON SCHEMA public TO liara;
EOF

# Migrations ausführen
cd /opt/liara/app
source ../venv/bin/activate
alembic upgrade head
```

### Schritt 5: Frontend Setup
```bash
cd /opt/liara/frontend
npm install
```

### Schritt 6: Systemd Services
```bash
# Backend Service
sudo systemctl enable liara.service
sudo systemctl start liara.service

# Frontend Service
sudo systemctl enable liara-frontend.service
sudo systemctl start liara-frontend.service
```

---

## 🔧 Script-Details

### install-ollama.sh

**Funktionen:**
1. Root-Check
2. Ollama-Installation via curl
3. Service-Start-Check
4. Sequential Model Downloads
5. Model-Verification

**Exit-Codes:**
- `0` - Erfolg
- `1` - Root-Rechte fehlen
- `2` - Installation fehlgeschlagen
- `3` - Model-Download fehlgeschlagen

**Log-Ausgabe:**
```
🚀 Ollama Installation für Liara
================================

✓ Root-Rechte bestätigt
📦 Installiere Ollama...
✓ Ollama installiert
⏳ Warte auf Ollama Service...
✓ Ollama Service läuft
📚 Lade Ollama-Modelle...
⬇️  Lade llama3.2:1b (700MB - schnell)...
[...]
✅ Installation abgeschlossen!
```

---

### setup-venv.sh

**Funktionen:**
1. Non-Root-Check
2. venv-Existenz-Prüfung
3. pip-Upgrade
4. requirements.txt Installation
5. Fallback: Manuelle Package-Installation
6. Frozen-Requirements Export

**Exit-Codes:**
- `0` - Erfolg
- `1` - Root-Ausführung verhindert
- `2` - venv-Erstellung fehlgeschlagen

**Log-Ausgabe:**
```
🐍 Liara Virtual Environment Setup
====================================

📦 Erstelle Virtual Environment...
✓ Virtual Environment erstellt
🔧 Aktiviere Virtual Environment...
✓ Virtual Environment aktiviert
⬆️  Upgrade pip...
✓ pip aktualisiert
📚 Installiere Dependencies...
✓ Dependencies installiert
✅ Setup abgeschlossen!
```

---

## 📊 Systemanforderungen

### Minimum
- **CPU:** 4 Cores
- **RAM:** 8 GB
- **Disk:** 60 GB frei
- **OS:** Debian 12 / Ubuntu 22.04+

### Empfohlen
- **CPU:** 6+ Cores
- **RAM:** 16 GB
- **Disk:** 100 GB SSD
- **OS:** Debian 12

---

## 🔍 Troubleshooting

### Ollama-Installation schlägt fehl
```bash
# Manuelle Installation
curl -fsSL https://ollama.com/install.sh | sudo sh

# Service-Status prüfen
systemctl status ollama

# Manueller Service-Start
sudo systemctl start ollama
```

### Model-Download hängt
```bash
# Stoppe Download
pkill ollama

# Neustart mit einzelnem Modell
ollama pull llama3.2:3b
```

### venv-Setup schlägt fehl
```bash
# Python-Version prüfen
python3 --version  # Sollte ≥3.11 sein

# Manuell erstellen
python3 -m venv /opt/liara/venv
source /opt/liara/venv/bin/activate
pip install --upgrade pip
```

### Permission-Fehler
```bash
# Eigentümer korrigieren
sudo chown -R $USER:$USER /opt/liara

# venv neu erstellen
rm -rf /opt/liara/venv
bash setup/setup-venv.sh
```

---

## 🧪 Verifikation

### Ollama-Check
```bash
# Models anzeigen
ollama list

# Test-Chat
ollama run llama3.2:3b "Hallo Liara"
```

### Python-Check
```bash
# venv aktivieren
source /opt/liara/venv/bin/activate

# Packages prüfen
pip list | grep -E "(fastapi|sqlalchemy|uvicorn)"

# Backend starten
cd /opt/liara/app
uvicorn main:app --reload
```

### Datenbank-Check
```bash
# PostgreSQL-Verbindung
psql -U liara -d liara_db -h localhost

# Tables prüfen
\dt
```

---

## 📝 Logs

### Ollama-Logs
```bash
# Service-Logs
journalctl -u ollama -n 50

# Ollama-Server-Logs
tail -f /var/log/ollama/ollama.log  # Falls vorhanden
```

### Liara-Backend-Logs
```bash
# Service-Logs
journalctl -u liara.service -n 50 -f

# Direkte Logs (wenn manuell gestartet)
cd /opt/liara/app
uvicorn main:app --reload --log-level debug
```

---

## 🔄 Updates

### Ollama updaten
```bash
# Ollama selbst
curl -fsSL https://ollama.com/install.sh | sudo sh

# Modelle aktualisieren
ollama list
ollama pull llama3.2:3b  # Beispiel
```

### Python-Dependencies updaten
```bash
source /opt/liara/venv/bin/activate
pip install --upgrade fastapi uvicorn sqlalchemy
pip freeze > requirements.txt
```

---

## 🗑️ Deinstallation

### Ollama entfernen
```bash
# Service stoppen
sudo systemctl stop ollama
sudo systemctl disable ollama

# Ollama deinstallieren
sudo rm -rf /usr/local/bin/ollama
sudo rm -rf ~/.ollama
sudo rm /etc/systemd/system/ollama.service
```

### Python venv entfernen
```bash
rm -rf /opt/liara/venv
```

### Komplett-Reset
```bash
# ACHTUNG: Löscht alle Daten!
sudo systemctl stop liara liara-frontend
sudo -u postgres psql -c "DROP DATABASE liara_db;"
rm -rf /opt/liara/venv
sudo rm -rf ~/.ollama
```

---

## 📚 Weitere Ressourcen

- [Ollama Dokumentation](https://ollama.com/docs)
- [FastAPI Dokumentation](https://fastapi.tiangolo.com)
- [PostgreSQL Setup](../docs/DATABASE_SETUP.md)
- [Liara Hauptdokumentation](../docs/README.md)

---

## ✅ Checklist

Nach erfolgreicher Installation:

- [ ] Ollama installiert (`ollama list`)
- [ ] 9 Modelle geladen
- [ ] Python venv erstellt
- [ ] Dependencies installiert (`pip list`)
- [ ] PostgreSQL Datenbank erstellt
- [ ] Alembic Migrations ausgeführt
- [ ] Backend läuft (`curl localhost:8100`)
- [ ] Frontend läuft (`curl localhost:5173`)
- [ ] Services aktiviert (`systemctl status liara`)

---

**🌙 Liara Setup Scripts - Automatisierte Installation für dein AI-System**
