# Copilot Instructions for Liara

## Architecture Overview

**Liara** is a full-stack system monitoring application with:
- **Backend**: FastAPI (Python) serving REST endpoints from `/opt/liara/app/`
- **Frontend**: React + Vite SPA from `/opt/liara/frontend/`

The backend uses `psutil` and `platform` modules for system metrics (CPU, memory, disk, uptime).

### Project Structure

```
liara/
├── api/
│   ├── routers/
│   ├── models/
│   ├── services/
│   └── __init__.py
├── core/
│   ├── config.py
│   ├── scheduler.py
│   └── database.py
├── frontend/
│   ├── html/
│   ├── css/
│   ├── js/
│   └── assets/
├── liara_engine/
│   ├── memory/
│   ├── nlp/
│   ├── actions/
│   └── __init__.py
├── tests/
├── requirements.txt
├── README.md
└── main.py
```

## Key Structural Patterns

### Backend Organization (FastAPI)

The backend follows a **modular router pattern**:

```
app/
├── main.py              # FastAPI app entry, includes routers
├── api/                 # API routers (endpoints)
│   ├── system.py        # /info endpoint (inline logic)
│   └── dashboard.py     # /dashboard/info endpoint (delegates to dashboard/)
└── dashboard/           # Business logic modules
    └── info.py          # get_dashboard_info() implementation
```

**Pattern**: API routers in `api/` may contain inline logic (like `api/system.py`) OR delegate to modules in parallel directories (`dashboard/`, `system/`). The `api/dashboard.py` router uses a prefix `/dashboard` and delegates to `dashboard/info.py`.

**Import convention**: 
- Routers are imported with aliases: `from api.system import router as system_router`
- Business logic uses relative imports from peer directories: `from dashboard.info import get_dashboard_info`

### Frontend Organization (React + Vite)

Standard Vite + React structure with:
- `src/App.jsx` - Main component
- `src/main.jsx` - React entry point with StrictMode
- Vite provides HMR, no custom config beyond defaults

Currently contains boilerplate React counter demo - not yet connected to backend.

## Development Workflows

### Running the Backend

```bash
cd /opt/liara/app
# Virtual environment at /opt/liara/venv (if exists)
source ../venv/bin/activate  
uvicorn main:app --reload
```

Backend runs on default port 8000. Key endpoints:
- `GET /` - Health check
- `GET /info` - System info (hostname, OS, CPU count, uptime)
- `GET /dashboard/info` - Detailed dashboard metrics (CPU load, memory, disk)

### Running the Frontend

```bash
cd /opt/liara/frontend
npm run dev        # Development server with HMR
npm run build      # Production build
npm run lint       # ESLint checks
```

Frontend runs on Vite's default port (typically 5173).

## Dependencies & Tech Stack

**Backend**:
- FastAPI (web framework)
- psutil (system metrics)
- platform (OS information)
- No requirements.txt found - dependencies may be in venv or manually installed

**Frontend**:
- React 19.2.0
- Vite 7.2.4 (build tool)
- ESLint with react-hooks and react-refresh plugins

## Important Notes

- `app/main.py.old` contains legacy monolithic API structure - **ignore this file**
- `system/info.py` exists but is empty - unused module
- No frontend-backend integration code exists yet (no fetch/axios calls to API)
- No environment configuration files (.env) - backend/frontend communicate via hardcoded URLs when implemented

## When Adding Features

**New backend endpoints**: 
1. Create router in `api/` directory
2. Import and include in `app/main.py` with `app.include_router()`
3. For complex logic, create separate module (like `dashboard/info.py`) and import into router

**Frontend API integration**: 
- Add fetch/axios calls in components
- Consider adding proxy in `vite.config.js` to avoid CORS during dev
