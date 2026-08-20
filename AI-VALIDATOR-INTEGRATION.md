# AI-Validator Integration für Liara

**Status:** ✅ Produktiv  
**Datum:** 3. Januar 2026  
**Version:** 1.0.0

---

## 📋 Übersicht

**AI-Validator** ist ein remote Code-Validierungs-Service, der über REST-API mit Liara verbunden ist. Er prüft Code auf Syntax-Fehler, Style-Issues und Linting-Probleme in 6+ Programmiersprachen.

### Netzwerk-Architektur

```
┌─────────────────────┐
│   Liara Backend     │
│  (192.168.178.50)   │
│  Port: 8100         │
└──────────┬──────────┘
           │ HTTP
           │ /validate/*
           ↓
┌─────────────────────────────────┐
│   AI-Validator Server           │
│   (192.168.178.150)             │
│   Port: 5000                    │
│   - Python Validator             │
│   - JavaScript/TypeScript        │
│   - Bash/Shell                   │
│   - JSON/YAML                    │
└─────────────────────────────────┘
```

---

## 🔧 Konfiguration

### AI-Validator Service (auf Liara)

**Datei:** `/opt/liara/app/services/ai_validator_service.py`

```python
# Configuration
VALIDATOR_HOST = "192.168.178.150"
VALIDATOR_PORT = 5000
VALIDATOR_URL = "http://192.168.178.150:5000"
VALIDATOR_TIMEOUT = 30.0
```

### Liara Routes

**Datei:** `/opt/liara/app/api/routers/validation_router.py`  
**Prefix:** `/validate`  
**Tags:** `validation`

---

## 📡 REST API Endpoints

### Health Check

```bash
GET /validate/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "AI-Validator",
  "endpoint": "http://192.168.178.150:5000",
  "timestamp": "2026-01-03T17:54:45.648005"
}
```

---

### Allgemeine Code-Validierung

```bash
POST /validate/code
Content-Type: application/json

{
  "code": "python code string",
  "language": "python|javascript|typescript|bash|json|yaml|c|cpp|go|rust|php|ruby|sql|html|css|java",
  "strict": false
}
```

**Unterstützte Sprachen:**
- `python` - Python Syntax + Ruff Linting
- `javascript` - JavaScript + ESLint
- `typescript` - TypeScript + TSC
- `bash` - Bash/Shell + ShellCheck
- `json` - JSON Format
- `yaml` - YAML Format
- `c` - C Code + GCC
- `cpp` / `c++` - C++ Code + G++
- `go` - Go Code + Go Tools
- `rust` - Rust Code + Rustc
- `php` - PHP Code + PHP Linter
- `ruby` - Ruby Code + Ruby Syntax Check
- `sql` - SQL Code
- `html` - HTML Code
- `css` - CSS Code
- `java` - Java Code + Javac

**Response:**
```json
{
  "language": "python",
  "status": "ok|warning|error",
  "timestamp": "2026-01-03T17:54:51.991435",
  "errors": [
    {
      "tool": "syntax",
      "message": "...",
      "line": null,
      "column": null,
      "severity": "error"
    }
  ],
  "warnings": [],
  "file": "/tmp/tmpXXXX.py",
  "latency_ms": 37.714
}
```

---

### Sprach-spezifische Endpoints

#### Python

```bash
POST /validate/python
```

#### JavaScript

```bash
POST /validate/javascript
```

#### TypeScript

```bash
POST /validate/typescript
```

#### Bash/Shell

```bash
POST /validate/bash
```

#### C

```bash
POST /validate/c
```

#### C++

```bash
POST /validate/cpp
```

#### Go

```bash
POST /validate/go
```

#### Rust

```bash
POST /validate/rust
```

#### PHP

```bash
POST /validate/php
```

#### Ruby

```bash
POST /validate/ruby
```

#### SQL

```bash
POST /validate/sql
```

#### HTML

```bash
POST /validate/html
```

#### CSS

```bash
POST /validate/css
```

#### Java

```bash
POST /validate/java
```

#### JSON

```bash
POST /validate/json
```

#### YAML

```bash
POST /validate/yaml
```

---

## 🧪 Beispiele

### Python Code validieren

```bash
curl -X POST http://localhost:8100/validate/python \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def hello():\n    print(\"Hello World\")",
    "strict": false
  }'
```

**Response (OK):**
```json
{
  "language": "python",
  "status": "ok",
  "timestamp": "2026-01-03T17:54:51.991435",
  "errors": [],
  "warnings": [],
  "file": "/tmp/tmpyuk63ce7.py",
  "latency_ms": 37.714
}
```

### Fehlerhafte Python Code

```bash
curl -X POST http://localhost:8100/validate/python \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def broken():\n  print(\"missing colon\"\n",
    "strict": true
  }'
```

**Response (Fehler):**
```json
{
  "language": "python",
  "status": "error",
  "timestamp": "2026-01-03T17:54:58.927075",
  "errors": [
    {
      "tool": "syntax",
      "message": "File \"/tmp/tmprwmg0c9w.py\", line 2\n    print(\"missing colon\"\n         ^\nSyntaxError: '(' was never closed\n",
      "line": null,
      "column": null,
      "severity": "error"
    }
  ],
  "warnings": [],
  "file": "/tmp/tmprwmg0c9w.py",
  "latency_ms": 34.598
}
```

---

## 🔍 Troubleshooting

### AI-Validator Server ist nicht erreichbar

```bash
# Status prüfen
curl -v http://192.168.178.150:5000/health

# SSH zum Server
ssh ai-validator@192.168.178.150

# Prozesse prüfen
ps aux | grep metrics-server

# Log anschauen
tail -f /tmp/validator-server.log
```

### Liara Backend Logs

```bash
sudo journalctl -u liara-backend -f
```

### Python Validierung funktioniert nicht

```bash
# Auf Validator-Server prüfen
ssh ai-validator@192.168.178.150

# Python + Ruff installiert?
python3 --version
ruff --version
```

### Performance-Optimierung

- **Timeout** in `ai_validator_service.py` erhöhen (Standard: 30s)
- **Async** ist bereits implementiert (asyncio)
- **Caching** kann hinzugefügt werden

---

## 📊 Monitoring & Metriken

### Health Check

```bash
curl http://localhost:8100/validate/health
```

### Remote Validator Metriken

```bash
# Allgemeine Metriken
curl http://192.168.178.150:5000/api/metrics

# Summary
curl http://192.168.178.150:5000/api/summary

# Workspaces
curl http://192.168.178.150:5000/api/workspaces
```

---

## 🚀 Geplante Erweiterungen

- [ ] **Auto-Fix** - Automatische Code-Korrektionen
- [ ] **Custom Rules** - Benutzerdefinierte Validierungsregeln
- [ ] **Performance Caching** - Ergebnisse cachen
- [ ] **Batch Validation** - Mehrere Dateien gleichzeitig
- [ ] **WebSocket Support** - Live-Validierung während Eingabe
- [ ] **Integration in Chat** - Auto-Validierung von Chat-generierten Codes

---

## 📁 Dateien

| Datei | Ort | Beschreibung |
|-------|-----|-------------|
| Service | `/opt/liara/app/services/ai_validator_service.py` | Client-Service |
| Router | `/opt/liara/app/api/routers/validation_router.py` | API Endpoints |
| Remote | `/opt/ai-validator/metrics-server-v2.py` | Validator Server |
| Config | `/opt/liara/app/main.py` | Router Registration |

---

## 🔐 Credentials

**AI-Validator SSH:**
```
Host: 192.168.178.150
User: ai-validator
Pass: ai-2026
```

---

## 📝 Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-01-03 | 1.0.0 | Initial Integration |
| - | 1.1.0 | (geplant) Caching |
| - | 1.2.0 | (geplant) Custom Rules |

---

## 👤 Kontakt & Support

- **Service Owner:** AI-Validator Team
- **Integration Owner:** Liara Development
- **Status:** ✅ Produktiv
- **SLA:** 99.9% Verfügbarkeit

---

**Last Updated:** 2026-01-03  
**Next Review:** 2026-02-03
