"""
🩺 System Health & Hardware Metrics Service
============================================
Provides real-time system resource metrics, hardware temperatures, uptime,
and health diagnostics for database & background services.
"""

import os
import time
import socket
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import psutil

logger = logging.getLogger(__name__)


def get_system_uptime() -> Dict[str, Any]:
    """Returns boot time and formatted uptime string."""
    try:
        boot_timestamp = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_timestamp)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} Tag{'e' if days != 1 else ''}")
        if hours > 0 or days > 0:
            parts.append(f"{hours} Std.")
        parts.append(f"{minutes} Min.")

        return {
            "uptime_seconds": uptime_seconds,
            "formatted": ", ".join(parts),
            "boot_time": datetime.fromtimestamp(boot_timestamp, timezone.utc).isoformat()
        }
    except Exception as e:
        logger.warning(f"Failed to get uptime: {e}")
        return {"uptime_seconds": 0, "formatted": "Unbekannt", "error": str(e)}


def get_hardware_temperatures() -> Dict[str, Any]:
    """Retrieves hardware temperatures via psutil or thermal sysfs."""
    temps: Dict[str, Any] = {}
    if hasattr(psutil, "sensors_temperatures"):
        try:
            raw_temps = psutil.sensors_temperatures()
            if raw_temps:
                for sensor_name, entries in raw_temps.items():
                    sensor_list = []
                    for entry in entries:
                        sensor_list.append({
                            "label": entry.label or sensor_name,
                            "current_c": entry.current,
                            "high_c": entry.high,
                            "critical_c": entry.critical
                        })
                    temps[sensor_name] = sensor_list
        except Exception as e:
            logger.debug(f"psutil sensors_temperatures not available: {e}")

    # Fallback to sysfs thermal if psutil returned nothing
    if not temps and os.path.exists("/sys/class/thermal"):
        try:
            for item in os.listdir("/sys/class/thermal"):
                if item.startswith("thermal_zone"):
                    temp_path = os.path.join("/sys/class/thermal", item, "temp")
                    type_path = os.path.join("/sys/class/thermal", item, "type")
                    if os.path.exists(temp_path):
                        with open(temp_path, "r") as f:
                            raw_val = f.read().strip()
                        zone_type = item
                        if os.path.exists(type_path):
                            with open(type_path, "r") as f:
                                zone_type = f.read().strip()
                        val_c = round(float(raw_val) / 1000.0, 1)
                        temps[zone_type] = [{"label": zone_type, "current_c": val_c}]
        except Exception as e:
            logger.debug(f"sysfs thermal read error: {e}")

    return temps


def get_system_metrics() -> Dict[str, Any]:
    """Gathers CPU, memory, disk, and load average metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count(logical=True)
    load1, load5, load15 = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)

    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "cores": cpu_count,
            "load_avg": [round(load1, 2), round(load5, 2), round(load15, 2)]
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "free_gb": round(mem.available / (1024**3), 2),
            "percent": round(mem.percent, 1)
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 1)
        },
        "uptime": get_system_uptime(),
        "temperatures": get_hardware_temperatures()
    }


def check_services_status() -> Dict[str, Any]:
    """Checks operational status of databases and critical backend components."""
    services: Dict[str, Any] = {}

    # 1. PostgreSQL Check
    try:
        from core.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            start_t = time.time()
            db.execute(text("SELECT 1"))
            latency_ms = round((time.time() - start_t) * 1000, 1)
            services["postgresql"] = {"status": "connected", "healthy": True, "latency_ms": latency_ms}
        finally:
            db.close()
    except Exception as e:
        services["postgresql"] = {"status": "error", "healthy": False, "error": str(e)[:120]}

    # 2. Redis Check
    try:
        from services.redis_service import get_redis_service
        redis_svc = get_redis_service()
        if redis_svc.client.ping():
            services["redis"] = {"status": "connected", "healthy": True}
        else:
            services["redis"] = {"status": "disconnected", "healthy": False}
    except Exception as e:
        services["redis"] = {"status": "error", "healthy": False, "error": str(e)[:120]}

    # 3. Neo4j Check
    try:
        from services.neo4j_service import get_neo4j_service
        neo4j_svc = get_neo4j_service()
        if neo4j_svc and hasattr(neo4j_svc, "is_connected") and neo4j_svc.is_connected():
            services["neo4j"] = {"status": "connected", "healthy": True}
        else:
            services["neo4j"] = {"status": "available", "healthy": True}
    except Exception as e:
        services["neo4j"] = {"status": "not_configured", "healthy": True}

    # 4. Ollama Check
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        import urllib.request
        req = urllib.request.Request(f"{ollama_host}/api/tags", headers={"User-Agent": "Liara-Health/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                services["ollama"] = {"status": "running", "healthy": True, "host": ollama_host}
            else:
                services["ollama"] = {"status": "degraded", "healthy": False, "http_status": resp.status}
    except Exception as e:
        services["ollama"] = {"status": "offline", "healthy": False, "error": str(e)[:100]}

    return services


def get_full_system_health(scope: str = "summary") -> Dict[str, Any]:
    """
    Returns system health report based on scope:
    - 'summary': High-level resources + services status
    - 'resources': Detailed CPU, RAM, Disk, Uptime
    - 'services': Detailed database & inference service status
    - 'temperatures': Hardware temperature sensors
    """
    metrics = get_system_metrics()
    services = check_services_status()

    all_services_healthy = all(s.get("healthy", False) for s in services.values())
    cpu_high = metrics["cpu"]["percent"] > 85.0
    mem_high = metrics["memory"]["percent"] > 90.0
    disk_high = metrics["disk"]["percent"] > 90.0

    overall_status = "healthy"
    if not all_services_healthy or disk_high:
        overall_status = "degraded"
    if cpu_high and mem_high:
        overall_status = "warning"

    res = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": scope
    }

    if scope in ("summary", "resources"):
        res["resources"] = {
            "cpu": metrics["cpu"],
            "memory": metrics["memory"],
            "disk": metrics["disk"],
            "uptime": metrics["uptime"]["formatted"]
        }

    if scope in ("summary", "services"):
        res["services"] = services

    if scope in ("summary", "temperatures"):
        res["temperatures"] = metrics["temperatures"]

    return res


def register_system_health_tools(registry) -> None:
    """Registers system health tool in ToolRegistry."""
    from services.tool_registry import ToolDefinition, ToolParameter, ToolCategory

    registry.register_tool(ToolDefinition(
        name="get_system_health",
        description=(
            "Ruft den aktuellen Systemstatus, CPU/RAM/Festplatten-Auslastung, Uptime, "
            "Hardware-Sensoren (Temperaturen) und den Zustand aller Hintergrunddienste "
            "(PostgreSQL, Redis, Neo4j, Ollama, Backend) ab."
        ),
        category=ToolCategory.INFORMATION,
        parameters=[
            ToolParameter(
                name="scope",
                type="string",
                description="Umfang der Abfrage: 'summary' (Standard: Übersicht), 'resources' (CPU/RAM/Disk), 'services' (Dienste/DBs), 'temperatures' (Hardware-Sensoren)",
                required=False,
                default="summary",
                enum=["summary", "resources", "services", "temperatures"]
            )
        ],
        function=_stub_fn,
        requires_consent=False,
        privacy_level="low"
    ))


async def _stub_fn(**kwargs):
    return {"error": "Not implemented"}
