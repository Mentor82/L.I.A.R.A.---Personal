# Liara - System Monitoring Application

Ein Full-Stack-System-Monitoring-Tool mit FastAPI-Backend und React-Frontend.

## Architektur

- **Backend**: FastAPI (Python) für REST API-Endpunkte
- **Frontend**: React + Vite für die Benutzeroberfläche
- **Monitoring**: psutil für Systemmetriken (CPU, Speicher, Festplatte)

## Projektstruktur

```
liara/
├── api/                 # API-Layer
│   ├── routers/        # API-Routen
│   ├── models/         # Datenmodelle
│   └── services/       # Business-Logik-Services
├── core/               # Kernkonfiguration
│   ├── config.py       # App-Konfiguration
│   ├── scheduler.py    # Task-Scheduler
│   └── database.py     # Datenbankverbindung
├── liara_engine/       # KI/ML-Komponenten
│   ├── memory/         # Speicherverwaltung
│   ├── nlp/           # NLP-Verarbeitung
│   └── actions/       # Action-Handler
├── tests/             # Test-Suite
└── main.py            # Hauptanwendung
```

## Installation

### Backend

```bash
cd /opt/liara/app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd /opt/liara/frontend
npm install
```

## Entwicklung

### Backend starten

```bash
cd /opt/liara/app
source venv/bin/activate
uvicorn main:app --reload
```

Backend läuft auf Port 8000.

### Frontend starten

```bash
cd /opt/liara/frontend
npm run dev
```

Frontend läuft auf Port 5173 (Vite-Standard).

## API-Endpunkte

- `GET /` - Health-Check
- `GET /info` - Systeminformationen
- `GET /dashboard/info` - Dashboard-Metriken

## Lizenz

Proprietär
