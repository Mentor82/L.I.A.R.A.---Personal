# Hailo-8L Chat Integration Deployment
**Datum:** 3. Januar 2026
**Status:** Code deployed, Service restart pending

## Was wurde deployed?
- backend_router.py (Backend selection + fallback)
- chat_hailo_integration.py (Vision detection)
- hailo_service.py (Hailo device API)
- hailo_router.py (REST + Prometheus)
- chat.py (Backend Router Integration)
- main.py (Hailo router included)

## Service restart erforderlich
sudo systemctl restart liara-api

## Tests
curl http://localhost:8000/hailo/health
curl -X POST http://localhost:8000/chat/message -d '{"message":"Hi"}'

## Rollback
cd /opt/liara && tar xzf /tmp/liara-backup-20260103-135122.tar.gz
