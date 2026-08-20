# Liara v2.7.0 Deployment Guide

## Multi-Threading with Gunicorn + Uvicorn Workers

### Overview
Version 2.7.0 introduces **true multi-processing** using Gunicorn as a process manager with multiple Uvicorn worker instances.

**Performance Gains:**
- Single-threaded: ~500 req/s
- Multi-threaded (17 workers): **~5300 req/s** (10x improvement)

---

## Prerequisites

- Python 3.11+
- PostgreSQL running
- 8 CPU cores (optimal: 17 workers = cores * 2 + 1)
- ~16 GB RAM recommended (workers use ~820 MB each)

---

## Installation Steps

### 1. Install Gunicorn

```bash
source /opt/liara/venv/bin/activate
pip install gunicorn==23.0.0
```

### 2. Update Systemd Service

```bash
sudo cp /opt/liara/patches/20251203_v2.7.0_multi_threading/liara-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable liara-backend.service
```

### 3. Disable Old Service

```bash
sudo systemctl stop liara.service
sudo systemctl disable liara.service
```

### 4. Update Scripts

```bash
cd /opt/liara
cp patches/20251203_v2.7.0_multi_threading/restart_backend.sh .
cp patches/20251203_v2.7.0_multi_threading/start_backend.sh .
chmod +x *.sh
```

### 5. Start Multi-Worker Backend

```bash
sudo systemctl start liara-backend
```

---

## Verification

### Check Worker Count
```bash
ps aux | grep gunicorn | grep -v grep | wc -l
```
**Expected:** 18 (1 master + 17 workers)

### Service Status
```bash
sudo systemctl status liara-backend
```

### Load Test
```bash
ab -n 1000 -c 50 http://localhost:8100/info
```
**Expected:** ~5000+ requests/second

### Monitor Workers
```bash
watch -n 1 'ps aux | grep gunicorn | grep -v grep'
```

---

## Architecture

```
┌─────────────────────────────────────┐
│   Systemd: liara-backend.service    │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │  Gunicorn      │  (Master Process)
         │  PID: 73043    │
         └───────┬────────┘
                 │
      ┌──────────┴──────────┐
      │  17 Uvicorn Workers │
      │  (FastAPI Servers)  │
      └─────────────────────┘
           ↓  Port 8100
      ┌─────────────────────┐
      │  Nginx Reverse      │
      │  Proxy              │
      └─────────────────────┘
```

---

## Configuration Files

### `/etc/systemd/system/liara-backend.service`
```ini
[Unit]
Description=Liara Backend (Gunicorn + Uvicorn Workers)
After=network.target postgresql.service docker.service
Wants=postgresql.service docker.service

[Service]
Type=simple
User=mirko
Group=mirko
WorkingDirectory=/opt/liara/app
Environment="PATH=/opt/liara/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/bin/bash -c 'WORKERS=$$(($$(nproc) * 2 + 1)); exec /opt/liara/venv/bin/gunicorn main:app --workers $$WORKERS --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8100 --log-level info --access-logfile /var/log/liara/access.log --error-logfile /var/log/liara/error.log'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## Troubleshooting

### Port Already in Use
```bash
sudo lsof -i :8100
sudo pkill -9 -f "uvicorn main:app"
sudo systemctl restart liara-backend
```

### Workers Not Spawning
Check error log:
```bash
tail -100 /var/log/liara/error.log
```

### High Failed Requests Under Load
- Issue: DB connection pool exhaustion
- Solution: Increase `POOL_SIZE` in `/opt/liara/app/core/database.py`
- Future: Migrate to async SQLAlchemy (Phase 2)

---

## Performance Tuning

### Optimal Worker Count
Formula: `CPU_CORES * 2 + 1`

- 4 cores → 9 workers
- 8 cores → 17 workers
- 16 cores → 33 workers

### Memory Usage
Each worker: ~820 MB RAM
Total (17 workers): ~14 GB

### Database Pool
Recommended settings:
```python
POOL_SIZE = 50
MAX_OVERFLOW = 100
```

---

## Rollback Plan

If issues occur:

```bash
# Stop new service
sudo systemctl stop liara-backend

# Re-enable old service
sudo systemctl enable liara.service
sudo systemctl start liara.service

# Restore old scripts
cd /opt/liara/backups/20251203_225552_v2.6.1_complete
cp restart_backend.sh /opt/liara/
cp start_backend.sh /opt/liara/
```

---

## Next Steps (Roadmap)

### Phase 2: Async Database (v2.8.0)
- Migrate to SQLAlchemy 2.0 async
- Install asyncpg
- Convert all `db.query()` to async
- Eliminate DB blocking calls

### Phase 3: Async HTTP (v2.9.0)
- Replace `requests` with `httpx.AsyncClient`
- Async Ollama calls
- Async web search
- Async location services

---

## Support

**Backup Location:** `/opt/liara/backups/20251203_231306_v2.7.0_multi_threading`
**Patch Location:** `/opt/liara/patches/20251203_v2.7.0_multi_threading`
**Logs:** `/var/log/liara/error.log`, `/var/log/liara/access.log`
