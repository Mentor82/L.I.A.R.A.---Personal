# 🗄️ PostgreSQL Setup - Liara Database

**Version:** 1.0  
**Erstellt:** 2025-12-03  
**Status:** ✅ Produktiv

---

## 📋 Übersicht

Liara nutzt **PostgreSQL 15** als primäre Datenbank für:
- Tasks & Aufgabenverwaltung
- Kalender & Terminplanung
- Notizen-System
- Memory & Pattern Recognition
- Packlisten & Routinen

---

## 🔧 Installation & Setup

### 1. PostgreSQL Installation

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

### 2. Datenbank & User erstellen

```bash
# Als postgres User
sudo -u postgres psql

# In psql:
CREATE DATABASE liara_db;
CREATE USER liara WITH PASSWORD 'liara_secure_2025';
GRANT ALL PRIVILEGES ON DATABASE liara_db TO liara;

# Schema-Rechte vergeben
\c liara_db
GRANT ALL ON SCHEMA public TO liara;
```

### 3. Python Dependencies

```bash
cd /opt/liara
source venv/bin/activate
pip install sqlalchemy psycopg2-binary alembic python-dotenv
```

---

## 📊 Datenbank-Schema

### Tasks Table
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    priority VARCHAR(20) DEFAULT 'medium',
    due_date TIMESTAMP,
    tags JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Felder:**
- `id` - Eindeutige Task-ID
- `title` - Aufgaben-Titel
- `description` - Detaillierte Beschreibung
- `completed` - Erledigt-Status
- `priority` - low, medium, high
- `due_date` - Fälligkeitsdatum
- `tags` - JSON-Array von Tags
- `created_at/updated_at` - Timestamps

### Calendar Events Table
```sql
CREATE TABLE calendar_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    location VARCHAR(255),
    event_type VARCHAR(50) DEFAULT 'meeting',
    all_day BOOLEAN DEFAULT FALSE,
    recurrence JSON,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Event Types:**
- `meeting` - Meetings/Besprechungen
- `reminder` - Erinnerungen
- `appointment` - Termine

**Recurrence Format:**
```json
{
    "frequency": "weekly",
    "interval": 1,
    "end_date": "2025-12-31"
}
```

### Notes Table
```sql
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags JSON DEFAULT '[]',
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Features:**
- Pinned Notes (wichtige Notizen oben)
- Archivierung
- Kategorien & Tags
- Full-text Search (geplant)

### Memories Table
```sql
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    memory_type VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSON NOT NULL,
    confidence INTEGER DEFAULT 50,
    last_confirmed TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memories_key ON memories(key);
```

**Memory Types:**
- `routine` - Erkannte Routinen
- `pattern` - Verhaltens-Muster
- `preference` - User-Präferenzen
- `fact` - Fakten über User

**Beispiel:**
```json
{
    "memory_type": "pattern",
    "key": "sleep_pattern",
    "value": {
        "usual_bedtime": "23:00",
        "usual_wake_time": "07:00",
        "sleep_quality_factors": ["stress", "exercise"]
    },
    "confidence": 85
}
```

### Packing Lists Table
```sql
CREATE TABLE packing_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trip_type VARCHAR(100),
    items JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Items Format:**
```json
[
    {"item": "Zahnbürste", "checked": false, "category": "hygiene"},
    {"item": "Ladekabel", "checked": true, "category": "electronics"}
]
```

### Routines Table
```sql
CREATE TABLE routines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    routine_type VARCHAR(50) NOT NULL,
    time_of_day VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    actions JSON NOT NULL,
    last_executed TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Routine Types:**
- `daily` - Täglich
- `weekly` - Wöchentlich
- `monthly` - Monatlich

**Actions Format:**
```json
[
    {
        "action": "remind",
        "params": {
            "message": "Zeit für Pause",
            "time": "14:00"
        }
    }
]
```

---

## 🔄 Migrations (Alembic)

### Neue Migration erstellen
```bash
cd /opt/liara/app
source ../venv/bin/activate
alembic revision --autogenerate -m "Description of changes"
```

### Migration ausführen
```bash
alembic upgrade head
```

### Migration rückgängig machen
```bash
alembic downgrade -1
```

### Migration-History
```bash
alembic history
```

---

## 🔐 Umgebungsvariablen

**Datei:** `/opt/liara/app/.env`

```env
DATABASE_URL=postgresql://liara:liara_secure_2025@localhost/liara_db
```

---

## 🛠️ SQLAlchemy Setup

**Datei:** `/opt/liara/app/core/database.py`

```python
from sqlalchemy import create_engine
from core.database import Base, get_db

# In FastAPI Endpoint:
@router.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    return tasks
```

---

## 📊 Nützliche Befehle

### PostgreSQL Shell
```bash
# Als postgres User verbinden
sudo -u postgres psql

# Als liara User verbinden
psql -U liara -d liara_db -h localhost
```

### Datenbank-Abfragen
```sql
-- Alle Tables anzeigen
\dt

-- Table-Struktur anzeigen
\d tasks

-- Alle Tasks anzeigen
SELECT * FROM tasks;

-- Tasks nach Priorität
SELECT * FROM tasks WHERE priority = 'high';

-- Nächste Termine
SELECT * FROM calendar_events 
WHERE start_time > NOW() 
ORDER BY start_time LIMIT 5;
```

### Backup & Restore
```bash
# Backup erstellen
pg_dump -U liara liara_db > liara_backup_$(date +%Y%m%d).sql

# Restore
psql -U liara liara_db < liara_backup_20251203.sql
```

---

## 🔍 Monitoring

### Connection-Check
```python
from core.database import check_connection

if check_connection():
    print("✅ Database connected")
else:
    print("❌ Database connection failed")
```

### Aktive Connections
```sql
SELECT * FROM pg_stat_activity WHERE datname = 'liara_db';
```

### Datenbank-Größe
```sql
SELECT pg_size_pretty(pg_database_size('liara_db'));
```

---

## 🚀 Performance-Tipps

### Indizes erstellen
```sql
-- Für häufige Abfragen
CREATE INDEX idx_tasks_completed ON tasks(completed);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_calendar_start_time ON calendar_events(start_time);
CREATE INDEX idx_notes_category ON notes(category);
```

### Connection Pooling
In `core/database.py` bereits konfiguriert:
- `pool_size=10` - Max 10 gleichzeitige Connections
- `max_overflow=20` - Bis zu 20 zusätzliche bei Bedarf
- `pool_pre_ping=True` - Connection-Check vor Nutzung

---

## 🔒 Sicherheit

### Passwort ändern
```sql
ALTER USER liara WITH PASSWORD 'neues_sicheres_passwort';
```

### Berechtigungen prüfen
```sql
\du liara
```

### Nur lokale Verbindungen erlauben
In `/etc/postgresql/15/main/pg_hba.conf`:
```
local   liara_db    liara                   md5
host    liara_db    liara   127.0.0.1/32    md5
```

---

## 📚 Weitere Ressourcen

- [PostgreSQL 15 Dokumentation](https://www.postgresql.org/docs/15/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [FastAPI + SQLAlchemy](https://fastapi.tiangolo.com/tutorial/sql-databases/)

---

## ✅ Status

**Aktueller Stand:**
- ✅ PostgreSQL 15 installiert
- ✅ Datenbank `liara_db` erstellt
- ✅ User `liara` konfiguriert
- ✅ 6 Base Tables erstellt
- ✅ Alembic Migrations aktiv
- ✅ SQLAlchemy ORM integriert
- ✅ Connection-Check im Startup

**Nächste Schritte:**
- [ ] API Endpoints für Tasks
- [ ] API Endpoints für Calendar
- [ ] API Endpoints für Notes
- [ ] Full-text Search für Notes
- [ ] Memory-System API
