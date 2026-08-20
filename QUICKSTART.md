# Liara - Schnellstart-Anleitung

## ⚡ Quick Start (Entwicklung)

### 1. Voraussetzungen prüfen

```bash
# Python Version
python3 --version  # Sollte 3.11+ sein

# Node.js Version
node --version     # Sollte 18+ sein

# PostgreSQL
sudo systemctl status postgresql

# Docker (für Neo4j/Redis)
docker --version

# Ollama
ollama --version
```

### 2. Projekt klonen/setup

```bash
# Zu Projektverzeichnis navigieren
cd /opt/liara

# Python Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Backend Dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic \
            python-dotenv python-jose passlib bcrypt redis neo4j \
            sentence-transformers requests psutil httpx

# Frontend Dependencies
cd frontend
npm install
cd ..
```

### 3. Datenbanken starten

```bash
# PostgreSQL (sollte bereits laufen)
sudo systemctl start postgresql

# Redis (Docker)
docker start liara-redis || docker run -d \
  --name liara-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:latest

# Neo4j (Docker)
docker start liara-neo4j || docker run -d \
  --name liara-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  --restart unless-stopped \
  neo4j:latest
```

### 4. Environment Variables

```bash
# .env Datei erstellen
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://liara_user:secure_password@localhost/liara_db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
REDIS_URL=redis://localhost:6379/0

# Auth
SECRET_KEY=your-secret-key-hier-32-zeichen-minimum
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Ollama
OLLAMA_HOST=http://localhost:11434

# Features
WEB_SEARCH_ENABLED=true
GUEST_MODE_ENABLED=true
EOF
```

### 5. Datenbank initialisieren

```bash
# PostgreSQL User und DB erstellen
sudo -u postgres psql << 'SQL'
CREATE DATABASE liara_db;
CREATE USER liara_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE liara_db TO liara_user;
\q
SQL

# Tabellen erstellen
cd app
python -c "from core.database import init_db; init_db()"
cd ..
```

### 6. Ollama Models laden

```bash
# Minimal Setup (schnell)
ollama pull llama3.2:1b  # Guest Mode
ollama pull llama3.2:3b  # User Mode

# Empfohlen (bessere Qualität)
ollama pull qwen2.5:3b
ollama pull deepseek-r1:7b
```

### 7. Services starten

**Terminal 1 - Backend:**
```bash
cd /opt/liara/app
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8100
```

**Terminal 2 - Frontend:**
```bash
cd /opt/liara/frontend
npm run dev
```

### 8. Zugriff testen

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8100
- **API Docs**: http://localhost:8100/docs
- **Neo4j Browser**: http://localhost:7474

---

## 🔐 Ersten Admin-User erstellen

```bash
cd /opt/liara/app
source ../venv/bin/activate
python << 'PYTHON'
from core.database import SessionLocal
from api.models.base_models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

admin = User(
    username="admin",
    email="admin@liara.local",
    full_name="Administrator",
    hashed_password=pwd_context.hash("admin123"),
    role="admin",
    is_active=True
)
db.add(admin)
db.commit()
print("✅ Admin-User erstellt: admin / admin123")
PYTHON
```

---

## 📱 Zugriff von anderen Geräten

### Vite Dev Server für Netzwerk freigeben:

```bash
# vite.config.js sollte bereits haben:
server: {
  host: '0.0.0.0',  # Auf allen Interfaces lauschen
  allowedHosts: ['liara', '192.168.178.50', 'localhost'],
}
```

### Von Tablet/Handy zugreifen:

```
http://192.168.178.50:5173  # Frontend (Dev)
http://192.168.178.50:8100  # Backend API
```

---

## 🔄 Production Build

### Frontend bauen:

```bash
cd /opt/liara/frontend
npm run build
# Output in: dist/
```

### nginx konfigurieren:

```bash
# /etc/nginx/sites-available/liara
sudo nano /etc/nginx/sites-available/liara

# Inhalt:
server {
    listen 80;
    server_name 192.168.178.50 liara.local;

    location /api/ {
        proxy_pass http://localhost:8100/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_buffering off;  # SSE Support
    }

    location / {
        root /opt/liara/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}

# Aktivieren:
sudo ln -s /etc/nginx/sites-available/liara /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Systemd Services:

```bash
# Backend
sudo systemctl start liara-backend
sudo systemctl enable liara-backend

# Frontend (für Dev-Server)
sudo systemctl start liara-frontend
sudo systemctl enable liara-frontend

# Status prüfen
sudo systemctl status liara-backend liara-frontend
```

---

## 🛠️ Nützliche Befehle

### Services verwalten:

```bash
# Status
systemctl status liara-backend liara-frontend

# Logs
sudo journalctl -u liara-backend -f
sudo journalctl -u liara-frontend -f

# Neu starten
sudo systemctl restart liara-backend
sudo systemctl restart liara-frontend

# Stoppen
sudo systemctl stop liara-backend liara-frontend
```

### Docker Container:

```bash
# Status
docker ps -a | grep liara

# Logs
docker logs liara-neo4j -f
docker logs liara-redis -f

# Neu starten
docker restart liara-neo4j liara-redis

# Stoppen/Starten
docker stop liara-neo4j liara-redis
docker start liara-neo4j liara-redis
```

### Datenbank-Zugriff:

```bash
# PostgreSQL
psql -U liara_user -d liara_db -h localhost

# Nützliche Queries:
SELECT * FROM users;
SELECT * FROM chat_messages ORDER BY timestamp DESC LIMIT 10;
SELECT COUNT(*) FROM tasks;

# Neo4j (Browser oder CLI)
docker exec -it liara-neo4j cypher-shell -u neo4j -p your_password

# Cypher Query:
MATCH (n) RETURN n LIMIT 10;
MATCH ()-[r:MENTIONED_IN]->() RETURN COUNT(r);
```

### Ollama Models:

```bash
# List Models
ollama list

# Pull Model
ollama pull llama3.2:3b

# Remove Model
ollama rm llama3.2:1b

# Model Info
ollama show llama3.2:3b
```

---

## 🐛 Troubleshooting

### Backend startet nicht:

```bash
# Logs prüfen
sudo journalctl -u liara-backend -n 100

# Manuell starten zum Debuggen
cd /opt/liara/app
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8100

# Port blockiert?
sudo lsof -i :8100
```

### Frontend Build-Fehler:

```bash
# Node Modules neu installieren
cd /opt/liara/frontend
rm -rf node_modules package-lock.json
npm install

# Cache leeren
npm cache clean --force
```

### Datenbank-Verbindung fehlschlägt:

```bash
# PostgreSQL läuft?
sudo systemctl status postgresql

# Connection testen
psql -U liara_user -d liara_db -h localhost

# Passwort zurücksetzen
sudo -u postgres psql
ALTER USER liara_user WITH PASSWORD 'new_password';
```

### Neo4j nicht erreichbar:

```bash
# Container läuft?
docker ps | grep neo4j

# Logs prüfen
docker logs liara-neo4j

# Neu starten
docker restart liara-neo4j

# Browser: http://localhost:7474
# Username: neo4j
# Password: your_password
```

### Redis-Probleme:

```bash
# Container Status
docker ps | grep redis

# Redis CLI testen
docker exec -it liara-redis redis-cli
> PING
PONG
> KEYS *
```

---

## ✅ Checkliste: Alles läuft?

- [ ] PostgreSQL: `sudo systemctl status postgresql`
- [ ] Neo4j: `docker ps | grep neo4j`
- [ ] Redis: `docker ps | grep redis`
- [ ] Ollama: `ollama list`
- [ ] Backend: `curl http://localhost:8100/`
- [ ] Frontend: Browser öffnen → http://localhost:5173
- [ ] Admin Login: admin / admin123
- [ ] Guest Mode: "Als Gast starten" Button
- [ ] Health Check: http://localhost:8100/admin/health/summary

---

## 📚 Weitere Ressourcen

- **Vollständige Features**: `/opt/liara/FEATURES.md`
- **README**: `/opt/liara/README.md`
- **API Docs**: http://localhost:8100/docs (FastAPI Swagger)
- **Copilot Instructions**: `/opt/liara/.github/copilot-instructions.md`

---

**Happy Coding! 🌙**
