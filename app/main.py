from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.system import router as system_router
from api.dashboard import router as dashboard_router
from api.routers.chat import router as chat_router
from api.routers.chat_streaming import router as chat_streaming_router
from api.routers.chat_sessions import router as chat_sessions_router
from api.routers.code_exec_router import router as code_exec_router
from api.routers.workspace_router import router as workspace_router
from api.routers.liara_router import router as liara_router
from api.routers.mood_router import router as mood_router
from api.routers.sentiment_router import router as sentiment_router
from api.routers.tasks_router import router as tasks_router
from api.routers.calendar_router import router as calendar_router
from api.routers.notes_router import router as notes_router
from api.routers.gpu_router import router as gpu_router
from api.routers.ollama_router import router as ollama_router
from api.routers.auth_router import router as auth_router
from api.routers.users_router import router as users_router
from api.routers.profile_router import router as profile_router
from api.routers.user_preferences_router import router as user_preferences_router
from api.routers.memory import router as memory_router
from api.routers.external_router import router as external_router
from api.routers.web_safety_router import router as web_safety_router
from api.routers.privacy_router import router as privacy_router
from api.routers.location_router import router as location_router
from api.routers.admin_health import router as admin_health_router
from api.routers.admin_router import router as admin_router
from api.routers.system_config_router import router as system_config_router
from api.routers.system_load import router as system_load_router
from api.routers.public import router as public_router
from api.routers.terminal_pty import router as terminal_pty_router
from api.routers.vision import router as vision_router
from api.routers.admin_logs import router as admin_logs_router
from api.routers.updater_router import router as updater_router
from api.routers.terminal_exec_router import router as terminal_exec_router
from api.routers.dashboard_activities import router as dashboard_activities_router
from api.routers.hailo_router import router as hailo_router
from api.routers.validation_router import router as validation_router
from api.routers.mcp_validation_router import router as mcp_validation_router
# REMOVED: from api.chat_session import router as chat_session_router (legacy - use api.routers.chat_sessions)
# REMOVED: from api.chat_message import router as chat_message_router (legacy - use api.routers.chat_sessions)
from datetime import datetime
import platform
import time
import psutil
import os

# Load environment variables from .env file
load_dotenv(dotenv_path="../.env")

# Database
from core.database import check_connection
# Multi-Backend Validator
from services.multi_backend_validator import get_validator
# Hailo RPi5 Client
from services.hailo_rpi5_client import initialize_rpi5_client, shutdown_rpi5_client

# Edge TPU Client (edge01)
from services.edgetpu_client import initialize_edgetpu_client, shutdown_edgetpu_client

# Redis / Neo4j singletons - close paths existed but nothing called them
# (issue #15 items 1/2) until the lifespan context below.
from services.redis_service import close_redis_service
from services.neo4j_service import close_neo4j_service

# Auth (optional)
from core.auth import verify_credentials

# Startzeit für Uptime
START_TIME = time.time()

# Persona Version Tracking
PERSONA_VERSION = "1.2.0"
PERSONA_CHANGELOG = {
    "1.2.0": "Enhanced Mood System mit Confidence + History (2025-12-03)",
    "1.1.0": "Tasks/Calendar/Notes APIs implemented (2025-12-02)",
    "1.0.0": "Initial Persona Definition (2025-12-01)"
}

# Auth ist erstmal deaktiviert für Frontend-Entwicklung
ENABLE_AUTH = os.getenv("LIARA_AUTH_ENABLED", "false").lower() == "true"
dependencies = [Depends(verify_credentials)] if ENABLE_AUTH else []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Single owner for every long-lived service's init/teardown (issue #15
    item 4) - previously split across `@app.on_event` hooks that only
    covered the validator/Hailo/EdgeTPU clients, while Redis/Neo4j had
    their own close()/close_*_service() helpers that nothing ever called
    (items 1/2), and the (unused - see core/scheduler.py's removal in this
    same change, item 3) scheduler had no owner at all. Each step is
    exception-isolated so one service failing to start/stop doesn't skip
    the others.
    """
    print("🌙 Liara API starting...")

    if check_connection():
        print("✅ PostgreSQL connection successful")
    else:
        print("❌ PostgreSQL connection failed!")

    print("🎬 Initializing Hailo RPi5 Client...")
    try:
        await initialize_rpi5_client()
        print("✅ Hailo RPi5 Client initialized (192.168.178.15:5000)")
    except Exception as e:
        print(f"⚠️  Hailo RPi5 Client initialization failed: {str(e)}")

    print("🎬 Initializing Edge TPU Client...")
    try:
        await initialize_edgetpu_client()
        print("✅ Edge TPU Client initialized (192.168.178.155:5001)")
    except Exception as e:
        print(f"⚠️  Edge TPU Client initialization failed: {str(e)}")

    print("🔍 Initializing Multi-Backend Validator...")
    try:
        validator = await get_validator()
        health = await validator.health_check()
        print(f"✅ Multi-Backend Validator initialized")
        print(f"   Primary (liara-core): {health['primary']['status']}")
        print(f"   Fallback (liara): {health['fallback']['status']}")
        print(f"   Active backend: {health['active']}")
    except Exception as e:
        print(f"⚠️  Multi-Backend Validator initialization failed: {str(e)}")

    print("✨ Liara API ready")

    yield

    print("🌙 Liara API shutting down...")
    try:
        validator = await get_validator()
        await validator.shutdown()
        print("✅ Multi-Backend Validator shutdown complete")
    except Exception as e:
        print(f"⚠️  Validator shutdown error: {str(e)}")

    try:
        await shutdown_rpi5_client()
        print("✅ Hailo RPi5 Client shutdown complete")
    except Exception as e:
        print(f"⚠️  Hailo RPi5 Client shutdown error: {str(e)}")

    try:
        await shutdown_edgetpu_client()
        print("✅ Edge TPU Client shutdown complete")
    except Exception as e:
        print(f"⚠️  Edge TPU Client shutdown error: {str(e)}")

    try:
        close_redis_service()
        print("✅ Redis client closed")
    except Exception as e:
        print(f"⚠️  Redis shutdown error: {str(e)}")

    try:
        close_neo4j_service()
        print("✅ Neo4j driver closed")
    except Exception as e:
        print(f"⚠️  Neo4j shutdown error: {str(e)}")

    print("👋 Liara API stopped")


app = FastAPI(
    title="🌙 Liara API",
    description="Your warm, calm and helpful AI assistant",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    dependencies=dependencies,  # Auth nur wenn LIARA_AUTH_ENABLED=true
    lifespan=lifespan,
)

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.178.50:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TEMPORARY diagnostic (workspace agent-chat 500 investigation) - writes any
# unhandled exception's full traceback to a plain file, since journalctl
# (StandardError=journal in the systemd unit) needs sudo we don't have here.
# Remove once the bug behind the 500 is found.
import traceback as _traceback
@app.exception_handler(Exception)
async def _debug_log_unhandled_exception(request, exc):
    with open("/opt/liara/app/liara_debug_traceback.log", "a") as f:
        f.write(f"\n--- {request.method} {request.url.path} ---\n")
        f.write("".join(_traceback.format_exception(type(exc), exc, exc.__traceback__)))
    from starlette.responses import PlainTextResponse
    return PlainTextResponse("Internal Server Error", status_code=500)

app.include_router(system_router)
app.include_router(dashboard_router)
app.include_router(auth_router)  # Authentication endpoints
app.include_router(users_router)  # User management (admin only)
app.include_router(profile_router)  # User profile management
app.include_router(user_preferences_router)  # User preferences (settings page, custom instructions, memory, personality)
app.include_router(memory_router)  # 4D Memory endpoints
app.include_router(external_router)  # Web Search & Location (Privacy-focused)
app.include_router(web_safety_router)  # Web Safety - 4-Layer Security
app.include_router(privacy_router)  # Privacy & Location Consent API
app.include_router(location_router)  # Location Detection & Management
app.include_router(admin_health_router)  # System Health Diagnostics (Admin)
app.include_router(system_config_router)  # System Configuration (Admin)
app.include_router(system_load_router)  # System Load (for SSE decision)
app.include_router(public_router)  # Public endpoints (no auth required)
app.include_router(admin_router, prefix="/admin", tags=["admin"])  # Admin Tools (Services, Terminal)
app.include_router(admin_logs_router)  # Admin Logs - System Log Reader
app.include_router(updater_router)  # Admin Updater - git status + patch history (read-only)
app.include_router(terminal_exec_router)  # Admin Terminal Exec - async JSON command execution (AI tab)
app.include_router(dashboard_activities_router)  # Dashboard Activities Widget
app.include_router(terminal_pty_router)  # WebSocket PTY Terminal
app.include_router(vision_router)  # Vision API - Bildanalyse mit LLaVA
app.include_router(chat_router)
app.include_router(chat_streaming_router)
app.include_router(chat_sessions_router)
app.include_router(code_exec_router)  # Sandboxed Code Execution (chat "Run" button) + session workspace files
app.include_router(workspace_router)  # Workspace v1 - file create/save/rename/delete + chat-context selection
app.include_router(liara_router)
app.include_router(mood_router)
app.include_router(sentiment_router)  # Live Sentiment Analysis
app.include_router(tasks_router)
app.include_router(calendar_router)
app.include_router(notes_router)
app.include_router(gpu_router)
app.include_router(ollama_router)
app.include_router(hailo_router)  # Hailo-8L NPU inference and metrics
app.include_router(validation_router)  # AI Validation - Remote code validation (AI-Validator)
app.include_router(mcp_validation_router)  # MCP Validation - Semantic code analysis via Ollama MCP
# REMOVED: Legacy chat_session_router and chat_message_router (use chat_sessions_router instead)

@app.get("/")
def root():
    return {
        "message": "🌙 Liara API is online and ready",
        "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),  # Already string, but ensure no datetime object leaks
        "endpoints": {
            "system": "/info",
            "dashboard": "/dashboard/info",
            "chat": {
                "message": "/chat/message",
                "models": "/chat/models",
                "models_summary": "/chat/models/summary",
                "model_select": "/chat/model/select",
                "status": "/chat/status"
            },
            "liara": {
                "status": "/liara/status",
                "health": "/liara/health",
                "about": "/liara/about",
                "persona": "/liara/persona"
            },
            "mood": {
                "status": "/mood/status",
                "update": "/mood/update",
                "detect": "/mood/detect",
                "modifiers": "/mood/modifiers",
                "reset": "/mood/reset",
                "states": "/mood/states"
            },
            "tasks": {
                "create": "POST /tasks",
                "list": "GET /tasks",
                "daily": "GET /tasks/daily",
                "weekly": "GET /tasks/weekly",
                "get": "GET /tasks/{id}",
                "update": "PUT /tasks/{id}",
                "delete": "DELETE /tasks/{id}",
                "complete": "POST /tasks/{id}/complete"
            },
            "calendar": {
                "create": "POST /calendar",
                "list": "GET /calendar",
                "today": "GET /calendar/today",
                "week": "GET /calendar/week",
                "conflicts": "GET /calendar/conflicts",
                "free_slots": "GET /calendar/free",
                "get": "GET /calendar/{id}",
                "update": "PUT /calendar/{id}",
                "delete": "DELETE /calendar/{id}"
            },
            "notes": {
                "create": "POST /notes",
                "list": "GET /notes",
                "search": "GET /notes/search",
                "categories": "GET /notes/categories",
                "tags": "GET /notes/tags",
                "get": "GET /notes/{id}",
                "update": "PUT /notes/{id}",
                "delete": "DELETE /notes/{id}",
                "pin": "POST /notes/{id}/pin",
                "archive": "POST /notes/{id}/archive"
            },
            "meta": "/meta",
            "health_full": "/health/full",
            "docs": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        }
    }


@app.get("/meta")
def get_meta():
    """Zentrale Metadaten über Liara."""
    import requests
    
    # Uptime berechnen
    uptime_seconds = int(time.time() - START_TIME)
    
    # Ollama Status
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        models = response.json().get("models", []) if response.status_code == 200 else []
        models_loaded = [m["name"] for m in models]
    except:
        models_loaded = []
    
    return {
        "name": "Liara",
        "version": "1.0.0",
        "runtime": "uvicorn",
        "python": platform.python_version(),
        "uptime_seconds": uptime_seconds,
        "uptime": f"{uptime_seconds // 60}m {uptime_seconds % 60}s",
        "default_model": "llama3.2:3b",
        "models_loaded": models_loaded,
        "models_count": len(models_loaded),
        "ready": len(models_loaded) > 0,
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}"
    }


@app.get("/health")
def health():
    """
    Lightweight health check for backend router.
    Returns 200 OK if backend is responsive.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/full")
def health_full():
    """Vollständiger Health-Status."""
    import requests
    
    # Ollama Check
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_status = "ok" if response.status_code == 200 else "error"
        models = response.json().get("models", []) if response.status_code == 200 else []
        models_available = [m["name"] for m in models]
    except:
        ollama_status = "offline"
        models_available = []
    
    # System Resources
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    return {
        "api": "ok",
        "ollama": ollama_status,
        "models_available": models_available,
        "models_count": len(models_available),
        "ram": {
            "total_gb": round(memory.total / (1024**3), 1),
            "used_gb": round(memory.used / (1024**3), 1),
            "percent": round(memory.percent, 1),
            "status": "ok" if memory.percent < 85 else "warning"
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": round(disk.percent, 1),
            "status": "ok" if disk.percent < 80 else "warning"
        },
        "persona": "active",
        "overall_status": "healthy" if ollama_status == "ok" else "degraded"
    }
